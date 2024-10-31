#!/bin/bash

generate_hashes() {
  local hash_type="$1"
  local hash_command="$2"
  echo "${hash_type}:"
  find "${COMPONENTS:-main}" -type f | while read -r file; do
    echo " $(${hash_command} "$file" | cut -d" " -f1) $(wc -c < "$file")"
  done
}

build_repo() {
  local release="$1"
  local deb_pool="_site/${release}/deb/pool/${COMPONENTS:-main}"
  local deb_dists="dists/${release}"
  local deb_dists_components="${deb_dists}/${COMPONENTS:-main}/binary-all"
  
  export GPG_TTY=""
  pushd "_site/${release}/deb" >/dev/null
  mkdir -p "${deb_dists_components}"
  echo "Scanning all downloaded DEB Packages and creating Packages file."
  dpkg-scanpackages pool/ > "${deb_dists_components}/Packages"
  gzip -9 < "${deb_dists_components}/Packages" > "${deb_dists_components}/Packages.gz"
  bzip2 -9 < "${deb_dists_components}/Packages" > "${deb_dists_components}/Packages.bz2"
  popd >/dev/null

  pushd "_site/${release}/deb/${deb_dists}" >/dev/null
  echo "Making Release file"
  {
    echo "Origin: ${ORIGIN}"
    echo "Label: ${REPO_OWNER}"
    echo "Suite: ${release}"
    echo "Codename: ${release}"
    echo "Version: 1.0"
    echo "Architectures: all"
    echo "Components: ${COMPONENTS:-main}"
    echo "Description: ${DESCRIPTION:-A repository for packages released by ${REPO_OWNER}}"
    echo "Date: $(date -Ru)"
    generate_hashes MD5Sum md5sum
    generate_hashes SHA1 sha1sum
    generate_hashes SHA256 sha256sum
  } > Release
  
  echo "Signing Release file"
  gpg --detach-sign --armor --sign < Release > Release.gpg
  gpg --detach-sign --armor --sign --clearsign < Release > InRelease
  echo "DEB repo built"
  popd >/dev/null
}

for release in equuleus sagitta current; do
  build_repo "$release"
done
