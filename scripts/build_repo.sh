#!/bin/bash
# Build Debian package repositories for VyOS
# Usage: ./build_repo.sh

set -euo pipefail

# Constants
readonly SITE_DIR="_site"
readonly SUPPORTED_BRANCHES=("rolling")
readonly DEB_COMPONENTS="main"
readonly SOURCE_DIR="packages"
ARCHITECTURES=("all" "amd64" "arm64")
# GPG key resolution: prefer GPG_FINGERPRINT (set by CI), fall back to GPG_KEY_ID
readonly GPG_KEY_ID="${GPG_FINGERPRINT:-${GPG_KEY_ID:-}}"
# GPG_TTY: only capture when running in an interactive terminal
if [[ -t 0 ]]; then
	export GPG_TTY
else
	unset GPG_TTY 2>/dev/null || true
fi

# Logging configuration
readonly DEBUG=false

# Check required environment variables and tools
check_env_vars() {
	# REPO_OWNER is required unless ORIGIN is set (e.g. from CI GPG step)
	if [[ -z "${REPO_OWNER:-}" ]]; then
		if [[ -n "${ORIGIN:-}" ]]; then
			REPO_OWNER="${ORIGIN}"
			info "Using ORIGIN (${ORIGIN}) as REPO_OWNER"
		else
			echo "Error: Required environment variable REPO_OWNER is not set" >&2
			exit 1
		fi
	fi

	# Verify GPG is properly configured
	if ! gpg --list-secret-keys >/dev/null 2>&1; then
		error "No GPG secret keys found. Repository signing will fail."
	fi

	if [[ -n "${GPG_KEY_ID}" ]]; then
		if ! gpg --list-secret-keys "${GPG_KEY_ID}" >/dev/null 2>&1; then
			error "Specified GPG key ${GPG_KEY_ID} not found"
		fi
		info "Using GPG key: ${GPG_KEY_ID}"
	fi
}

log_message() {
	local level="$1"
	local message="$2"
	echo "${level}: ${message}" >&2
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
		info "Successfully moved ${moved} .deb packages"
	fi
}

move_sources() {
	local branch="$1"
	local target_dir="$2"
	local source_path="${SOURCE_DIR}/${branch}"
	local moved=0

	if [[ ! -d "${source_path}" ]]; then
		warning "Source directory ${source_path} not found, skipping source move"
		return 0
	fi

	info "Moving source packages from ${source_path}..."
	mkdir -p "${target_dir}"
	# Source package file extensions: .dsc, .tar.gz, .tar.xz, .tar.bz2, .orig.tar.*, .debian.tar.*, .changes
	local source_exts=("*.dsc" "*.tar.gz" "*.tar.xz" "*.tar.bz2" "*.changes")
	for pattern in "${source_exts[@]}"; do
		while IFS= read -r -d '' file; do
			if mv "$file" "${target_dir}/"; then
				((moved++))
			else
				error "Failed to move source file $file"
			fi
		done < <(find "${source_path}" -name "${pattern}" -type f -print0)
	done

	if ((moved == 0)); then
		warning "No source packages found in ${source_path}"
	else
		info "Successfully moved ${moved} source package files"
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
	move_sources "${branch}" "${deb_pool}"

	# Create component directories for each architecture
	for arch in "${ARCHITECTURES[@]}"; do
		local deb_dists_components="${deb_dists}/${DEB_COMPONENTS}/binary-${arch}"
		mkdir -p "${deb_dists_components}"

		# Generate package information for this architecture
		pushd "${deb_base}" >/dev/null || exit 1
		info "Scanning packages for architecture ${arch}..."

		# Use -a option to filter by architecture
		if ! dpkg-scanpackages -a "${arch}" "pool/${DEB_COMPONENTS}" >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages" 2>/dev/null; then
			warning "Package scanning for ${arch} failed"
			# Create an empty Packages file so compression doesn't fail
			touch "dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages"
		fi

		# Compress package information
		gzip -9n >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages.gz" <"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages"
		bzip2 -9 >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages.bz2" <"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages"
		if command -v xz >/dev/null 2>&1; then
			xz -9 >"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages.xz" <"dists/${branch}/${DEB_COMPONENTS}/binary-${arch}/Packages"
		fi

		popd >/dev/null || exit 1
	done

	# Generate source package index
	local deb_dists_source="${deb_dists}/${DEB_COMPONENTS}/source"
	mkdir -p "${deb_dists_source}"

	pushd "${deb_base}" >/dev/null || exit 1
	info "Scanning source packages..."
	dpkg-scansources "pool/${DEB_COMPONENTS}" >"dists/${branch}/${DEB_COMPONENTS}/source/Sources" 2>/dev/null || true
	gzip -9n >"dists/${branch}/${DEB_COMPONENTS}/source/Sources.gz" <"dists/${branch}/${DEB_COMPONENTS}/source/Sources"
	bzip2 -9 >"dists/${branch}/${DEB_COMPONENTS}/source/Sources.bz2" <"dists/${branch}/${DEB_COMPONENTS}/source/Sources"
	if command -v xz >/dev/null 2>&1; then
		xz -9 >"dists/${branch}/${DEB_COMPONENTS}/source/Sources.xz" <"dists/${branch}/${DEB_COMPONENTS}/source/Sources"
	fi
	popd >/dev/null || exit 1

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

	# Build GPG signing commands
	local gpg_common_opts=(--batch --yes --pinentry-mode loopback)
	local gpg_sign_cmd=(gpg "${gpg_common_opts[@]}" --detach-sign --armor)
	local gpg_clearsign_cmd=(gpg "${gpg_common_opts[@]}" --clearsign)

	if [[ -n "${GPG_KEY_ID}" ]]; then
		gpg_sign_cmd+=(--local-user "${GPG_KEY_ID}")
		gpg_clearsign_cmd+=(--local-user "${GPG_KEY_ID}")
	fi

	if ! "${gpg_sign_cmd[@]}" --output Release.gpg <Release; then
		error "GPG signing failed for Release.gpg"
	fi

	if ! "${gpg_clearsign_cmd[@]}" --output InRelease <Release; then
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
}

main() {
	# Set up cleanup trap
	trap cleanup EXIT INT TERM

	# Check environment variables
	info "Starting repository build process"
	check_env_vars

	# Verify required tools
	info "Checking required tools"
	local required_cmds=(dpkg-scanpackages dpkg-scansources gpg gzip bzip2 find sort awk md5sum sha1sum sha256sum)
	# Check for xz separately — it's recommended but not required
	if ! command -v xz >/dev/null 2>&1; then
		warning "xz not found — .xz compressed indices will not be generated"
	fi
	for cmd in "${required_cmds[@]}"; do
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
