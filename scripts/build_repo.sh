#!/bin/bash
# Build Debian package repositories for VyOS
# Usage: ./build_repo.sh

set -euo pipefail

# Constants
readonly SITE_DIR="_site"
readonly SUPPORTED_BRANCHES=("rolling")
readonly DEB_COMPONENTS="main"
readonly SOURCE_DIR="packages"
readonly GPG_TTY=$(tty)
readonly ARCHITECTURES=("all" "amd64" "arm64")
readonly GPG_KEY_ID="${GPG_KEY_ID:-}" # Optional environment variable for specific key

# Logging configuration
readonly DEBUG=false

# Check required environment variables and tools
check_env_vars() {
	local required_vars=("REPO_OWNER")
	for var in "${required_vars[@]}"; do
		if [[ -z "${!var:-}" ]]; then
			echo "Error: Required environment variable $var is not set"
			exit 1
		fi
	done

	# Verify GPG is properly configured
	if ! gpg --list-secret-keys >/dev/null 2>&1; then
		error "No GPG secret keys found. Repository signing will fail."
	fi

	if [[ -n "${GPG_KEY_ID}" ]]; then
		if ! gpg --list-secret-keys "${GPG_KEY_ID}" >/dev/null 2>&1; then
			error "Specified GPG key ${GPG_KEY_ID} not found"
		fi
	fi
}

log_message() {
	local level="$1"
	local message="$2"
	echo "${level}: ${message}"
	if ${DEBUG}; then
		echo "${level}: ${message}" >&2
	fi
}

error() {
	log_message "ERROR" "$1"
	exit 1
}

warning() {
	log_message "WARNING" "$1"
}

info() {
	log_message "INFO" "$1"
}

move_debs() {
	local branch="$1"
	local target_dir="$2"
	local source_path="${SOURCE_DIR}/${branch}"
	local moved=0

	if [[ ! -d "${source_path}" ]]; then
		warning "Source directory ${source_path} not found, skipping move"
		return 0
	fi

	info "Moving .deb packages from ${source_path}..."
	mkdir -p "${target_dir}"
	while IFS= read -r -d '' file; do
		if mv "$file" "${target_dir}/"; then
			((moved++))
		else
			error "Failed to move $file"
		fi
	done < <(find "${source_path}" -name "*.deb" -type f -print0)

	if ((moved == 0)); then
		warning "No .deb packages found in ${source_path}"
	else
		info "Successfully moved ${moved} packages"
	fi
}

build_repo() {
	local branch="$1"

	# Define paths
	local deb_base="${SITE_DIR}/deb"
	local deb_pool="${deb_base}/pool/${DEB_COMPONENTS}"
	local deb_dists="${deb_base}/dists/${branch}"

	info "Building repository for ${branch}..."

	# Create repository structure and move packages
	mkdir -p "${deb_pool}"
	move_debs "${branch}" "${deb_pool}"

	# Create component directories for each architecture
	for arch in "${ARCHITECTURES[@]}"; do
		local deb_dists_components="${deb_dists}/${DEB_COMPONENTS}/binary-${arch}"
		mkdir -p "${deb_dists_components}"

		# Generate package information for this architecture
		pushd "${deb_base}" >/dev/null || exit 1
		info "Scanning packages for architecture ${arch}..."

		# Use -a option to filter by architecture
		if ! dpkg-scanpackages -a "${arch}" "pool/${DEB_COMPONENTS}" >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages" 2>&1; then
			# For architecture "all", also try without the -a flag if it fails
			if [[ "${arch}" == "all" ]] && ! dpkg-scanpackages "pool/${DEB_COMPONENTS}" >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages" 2>&1; then
				warning "Package scanning for ${arch} failed even without architecture filtering"
			else
				warning "Package scanning for ${arch} may have had issues"
			fi
		fi

		# Compress package information
		gzip -9 >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages.gz" <"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages"
		bzip2 -9 >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages.bz2" <"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages"

		popd >/dev/null || exit 1
	done

	# Generate and sign Release file in the correct location (dists/${branch}/)
	pushd "${deb_base}/dists/${branch}" >/dev/null || exit 1
	info "Generating Release file..."
	# First create the basic Release file information
	{
		echo "Origin: VyOS"
		echo "Label: ${REPO_OWNER}"
		echo "Suite: ${branch}"
		echo "Codename: ${branch}"
		echo "Version: 1.0"
		echo "Architectures: all amd64 arm64"
		echo "Components: ${DEB_COMPONENTS}"
		echo "Description: A repository for packages released by ${REPO_OWNER}"
		echo "Date: $(date -Ru)"
	} >Release

	# Generate hashes for Release file
	local hash_cmds=("MD5Sum:md5sum" "SHA1:sha1sum" "SHA256:sha256sum")
	for hc in "${hash_cmds[@]}"; do
		local hash_name="${hc%%:*}"
		local hash_cmd="${hc##*:}"

		echo "${hash_name}:" >>Release
		find "${DEB_COMPONENTS}" -type f -not -path "*/\.*" | sort | while read -r filepath; do
			if [[ "${filepath}" != "Release" && "${filepath}" != "Release.gpg" && "${filepath}" != "InRelease" ]]; then
				file_hash=$("${hash_cmd}" "${filepath}" | awk '{print $1}')
				# wc -c output can vary, using awk and redirecting input is the most portable way to get just the size
				file_size=$(wc -c <"${filepath}" | awk '{print $1}')
				echo " ${file_hash} ${file_size} ${filepath}" >>Release
			fi
		done
	done

	# Verify Release file has hash entries
	info "Verifying Release file contents..."
	if ! grep -q "^MD5Sum:" "Release" || ! grep -A 1 "MD5Sum:" "Release" | grep -q "^ "; then
		warning "No MD5Sum entries found in Release file. Repository may be empty or hash generation failed."
		# Add debug output
		echo "Current directory: $(pwd)"
		echo "Files in current directory: $(ls -la)"
		echo "Content of Release file:"
		cat Release
	fi

	info "Signing Release file..."
	export GPG_TTY

	# Use specified key if available
	local gpg_sign_cmd="gpg --detach-sign --armor"
	local gpg_clearsign_cmd="gpg --clearsign"

	if [[ -n "${GPG_KEY_ID}" ]]; then
		gpg_sign_cmd="${gpg_sign_cmd} --local-user ${GPG_KEY_ID}"
		gpg_clearsign_cmd="${gpg_clearsign_cmd} --local-user ${GPG_KEY_ID}"
	fi

	if ! ${gpg_sign_cmd} >Release.gpg <Release; then
		error "GPG signing failed for Release.gpg"
	fi

	if ! ${gpg_clearsign_cmd} >InRelease <Release; then
		error "GPG signing failed for InRelease"
	fi

	popd >/dev/null || exit 1

	echo "Repository built successfully for ${branch}"
}

cleanup() {
	# Clean up any temporary files or failed builds
	if [[ -d "${SITE_DIR}/packages" ]]; then
		info "Cleaning up packages directory"
		rm -rf "${SITE_DIR}/packages"
	fi
	if [[ -n "${temp_dir:-}" ]]; then
		info "Cleaning up temporary directory"
		rm -rf "${temp_dir}"
	fi
}

main() {
	# Set up cleanup trap
	trap cleanup EXIT INT TERM

	# Check environment variables
	info "Starting repository build process"
	check_env_vars

	# Verify required tools
	info "Checking required tools"
	for cmd in dpkg-scanpackages gpg gzip bzip2 find sort awk md5sum sha1sum sha256sum; do
		if ! command -v "$cmd" >/dev/null 2>&1; then
			error "Required command '$cmd' not found"
		fi
	done

	# Build repositories for all branches
	info "Building repositories for supported branches"
	for branch in "${SUPPORTED_BRANCHES[@]}"; do
		if ! build_repo "$branch"; then
			error "Failed to build repository for ${branch}"
		fi
	done

	# Clean up packages directory
	info "Final cleanup"
	rm -rf "${SITE_DIR}/packages"

	info "All repositories built successfully"
	echo "All repositories built successfully"
}

main "$@"
