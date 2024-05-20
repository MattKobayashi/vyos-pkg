#!/bin/bash
# Original source: https://github.com/terminate-notice/terminate-notice.github.io/blob/main/.github/scripts/build_repos.sh
generate_hashes() {
  HASH_TYPE="$1"
  HASH_COMMAND="$2"
  echo "${HASH_TYPE}:"
  find "${COMPONENTS:-main}" -type f | while read -r file
  do
    echo " $(${HASH_COMMAND} "$file" | cut -d" " -f1) $(wc -c "$file")"
  done
}

main() {
  DEB_POOL="_site/${SUITE}/deb/pool/${COMPONENTS:-main}"
  DEB_DISTS="dists/${SUITE:-stable}"
  DEB_DISTS_COMPONENTS="${DEB_DISTS}/${COMPONENTS:-main}/binary-all"
  GPG_TTY=""
  export GPG_TTY
  pushd _site/${SUITE}/deb >/dev/null
  mkdir -p "${DEB_DISTS_COMPONENTS}"
  echo "Scanning all downloaded DEB Packages and creating Packages file."
  dpkg-scanpackages --arch all pool/ > "${DEB_DISTS_COMPONENTS}/Packages"
  gzip -9 > "${DEB_DISTS_COMPONENTS}/Packages.gz" < "${DEB_DISTS_COMPONENTS}/Packages"
  bzip2 -9 > "${DEB_DISTS_COMPONENTS}/Packages.bz2" < "${DEB_DISTS_COMPONENTS}/Packages"
  popd >/dev/null
  pushd "_site/${SUITE}/deb/${DEB_DISTS}" >/dev/null
  echo "Making Release file"
  {
    echo "Origin: ${ORIGIN}"
    echo "Label: ${REPO_OWNER}"
    echo "Suite: ${SUITE:-stable}"
    echo "Codename: ${SUITE:-stable}"
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
  gpg --detach-sign --armor --sign > Release.gpg < Release
  gpg --detach-sign --armor --sign --clearsign > InRelease < Release
  echo "DEB repo built"
  popd >/dev/null
}
main
