#!/bin/bash
# Build Debian package repositories for VyOS
# Usage: ./build_repo.sh

set -euo pipefail

# Constants
readonly SITE_DIR="_site"
readonly SUPPORTED_BRANCHES=("equuleus" "sagitta" "current")
readonly DEB_COMPONENTS="${COMPONENTS:-main}"
readonly GPG_TTY=""

generate_hashes() {
    local hash_type="$1"
    local hash_command="$2"
    echo "${hash_type}:"
    find "${DEB_COMPONENTS}" -type f -printf "%P\n" | while read -r file; do
        echo " $(${hash_command} "$file" | cut -d" " -f1) $(wc -c "$file")"
    done
}

build_repo() {
    local branch="$1"
    
    # Define paths
    local deb_base="${SITE_DIR}/${branch}/deb"
    local deb_pool="${deb_base}/pool/${DEB_COMPONENTS}"
    local deb_dists="dists/${branch}"
    local deb_dists_components="${deb_dists}/${DEB_COMPONENTS}/binary-all"
    
    echo "Building repository for ${branch}..."
    
    # Create repository structure
    mkdir -p "${deb_base}/${deb_dists_components}"
    
    # Generate package information
    pushd "${deb_base}" >/dev/null || exit 1
    echo "Scanning packages and creating Packages file..."
    if ! dpkg-scanpackages pool/ > "${deb_dists_components}/Packages"; then
        echo "Error: Package scanning failed"
        exit 1
    fi
    
    # Compress package information
    gzip -9 > "${deb_dists_components}/Packages.gz" < "${deb_dists_components}/Packages"
    bzip2 -9 > "${deb_dists_components}/Packages.bz2" < "${deb_dists_components}/Packages"
    
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
    gpg --detach-sign --armor --sign > Release.gpg < Release
    gpg --detach-sign --armor --sign --clearsign > InRelease < Release
    
    popd >/dev/null || exit 1
    popd >/dev/null || exit 1
    
    echo "Repository built successfully for ${branch}"
}

main() {
    # Verify required tools
    for cmd in dpkg-scanpackages gpg gzip bzip2; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: Required command '$cmd' not found"
            exit 1
        fi
    
    # Build repositories for all branches
    for branch in "${SUPPORTED_BRANCHES[@]}"; do
        build_repo "$branch"
    done
}

main "$@"
