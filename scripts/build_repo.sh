#!/bin/bash
# Build Debian package repositories for VyOS
# Usage: ./build_repo.sh

set -euo pipefail

# Constants
readonly SITE_DIR="_site"
readonly SUPPORTED_BRANCHES=("current" "sagitta")
readonly DEB_COMPONENTS="${COMPONENTS:-main}"
readonly SOURCE_DIR="${SOURCE_DIR:-packages}"
readonly GPG_TTY=$(tty)

# Check required environment variables
check_env_vars() {
    local required_vars=("REPO_OWNER")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo "Error: Required environment variable $var is not set"
            exit 1
        fi
    done
}

generate_hashes() {
    local hash_type="$1"
    local hash_command="$2"
    
    echo "${hash_type}:"
    # Change to components directory before generating hashes
    cd "${DEB_COMPONENTS}" || exit 1
    find . -type f -printf "%P\n" | while read -r file; do
        echo " $(${hash_command} "$file" | cut -d" " -f1) $(wc -c "$file")"
    done
    cd - >/dev/null || exit 1
}

move_debs() {
    local branch="$1"
    local target_dir="$2"
    local source_path="${SOURCE_DIR}/${branch}"

    if [[ ! -d "${source_path}" ]]; then
        echo "Warning: Source directory ${source_path} not found, skipping move"
        return 0
    fi

    echo "Moving .deb packages from ${source_path}..."
    mkdir -p "${target_dir}"
    if ! find "${source_path}" -name "*.deb" -type f -exec mv {} "${target_dir}/" \;; then
        echo "Warning: No .deb packages found in ${source_path}"
    fi
}

build_repo() {
    local branch="$1"
    
    # Define paths
    local deb_base="${SITE_DIR}/${branch}/deb"
    local deb_pool="${deb_base}/pool/${DEB_COMPONENTS}"
    local deb_dists="${deb_base}/dists/${branch}"
    local deb_dists_components="${deb_dists}/${DEB_COMPONENTS}/binary-all"
    
    echo "Building repository for ${branch}..."
    
    # Create repository structure and move packages
    mkdir -p "${deb_pool}"
    mkdir -p "${deb_dists_components}"
    move_debs "${branch}" "${deb_pool}"
    
    # Generate package information
    pushd "${deb_base}" >/dev/null || exit 1
    echo "Scanning packages and creating Packages file..."
    if ! dpkg-scanpackages "pool/${DEB_COMPONENTS}" > "dists/${branch}/${DEB_COMPONENTS}/binary-all/Packages" 2>/dev/null; then
        echo "Error: Package scanning failed"
        exit 1
    fi
    
    # Compress package information
    gzip -9 > "dists/${branch}/${DEB_COMPONENTS}/binary-all/Packages.gz" < "dists/${branch}/${DEB_COMPONENTS}/binary-all/Packages"
    bzip2 -9 > "dists/${branch}/${DEB_COMPONENTS}/binary-all/Packages.bz2" < "dists/${branch}/${DEB_COMPONENTS}/binary-all/Packages"
    
    # Generate and sign Release file
    pushd "${deb_dists}" >/dev/null || exit 1
    echo "Generating Release file..."
    {
        echo "Origin: ${ORIGIN:-VyOS}"
        echo "Label: ${REPO_OWNER}"
        echo "Suite: ${branch}"
        echo "Codename: ${branch}"
        echo "Version: 1.0"
        echo "Architectures: all"
        echo "Components: ${DEB_COMPONENTS}"
        echo "Description: ${DESCRIPTION:-A repository for packages released by ${REPO_OWNER}}"
        echo "Date: $(date -Ru)"
        generate_hashes MD5Sum md5sum
        generate_hashes SHA1 sha1sum
        generate_hashes SHA256 sha256sum
    } > Release

    echo "Signing Release file..."
    export GPG_TTY
    if ! gpg --detach-sign --armor --sign > Release.gpg < Release; then
        echo "Error: GPG signing failed for Release.gpg"
        exit 1
    fi
    if ! gpg --detach-sign --armor --sign --clearsign > InRelease < Release; then
        echo "Error: GPG signing failed for InRelease"
        exit 1
    fi
    
    popd >/dev/null || exit 1
    popd >/dev/null || exit 1
    
    echo "Repository built successfully for ${branch}"
}

cleanup() {
    if [[ -n "${temp_dir:-}" ]]; then
        rm -rf "$temp_dir"
    fi
}

main() {
    # Set up cleanup trap
    trap cleanup EXIT

    # Check environment variables
    check_env_vars
    
    # Verify required tools
    for cmd in dpkg-scanpackages gpg gzip bzip2; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Build repositories for all branches
    for branch in "${SUPPORTED_BRANCHES[@]}"; do
        build_repo "$branch"
    done
}

main "$@"
