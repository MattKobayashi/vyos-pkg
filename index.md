---
layout: home
title: Unofficial VyOS .deb Packages Repository
---
Since the maintainers of the VyOS project have <a href="https://blog.vyos.io/community-contributors-userbase-and-lts-builds" target="_blank">decided</a> that they won't permit external access to their own package repositories anymore, I've set up my own unofficial one.

## How to use

### Using with `vyos-build` for `equuleus` release train

Run the `configure` script from the <a href="https://github.com/vyos/vyos-build/tree/equuleus" target="_blank">`vyos-build` repository</a>, passing the --vyos-mirror argument. Then run `sudo make iso`:

```
sudo ./configure --architecture amd64 --build-by "j.randomhacker@vyos.io" --vyos-mirror "[trusted=yes] {{ site.url }}/vyos-pkg/equuleus/deb"
sudo make iso
```

### Using with `vyos-build` for `sagitta` release train

Run the `build-vyos-image` script from the <a href="https://github.com/vyos/vyos-build/tree/sagitta" target="_blank">`vyos-build` repository</a>, passing the --vyos-mirror argument:

```
sudo ./build-vyos-image iso --architecture amd64 --build-by "j.randomhacker@vyos.io" --vyos-mirror "[trusted=yes] {{ site.url }}/vyos-pkg/sagitta/deb"
```

### Using with `vyos-build` for `current` release train

Run the `build-vyos-image` script from the <a href="https://github.com/vyos/vyos-build/tree/current" target="_blank">`vyos-build` repository</a>, passing the --vyos-mirror argument:

```
sudo ./build-vyos-image iso --architecture amd64 --build-by "j.randomhacker@vyos.io" --vyos-mirror "[trusted=yes] {{ site.url }}/vyos-pkg/current/deb"
```

## How to contribute?

Please contribute changes and bug reports in the relevant repository above.

Have a security issue? Please email the repository owner with details.

Have your own action? Please create a <a href="https://mattkobayashi.github.io/vyos-pkg.github.io/pulls" target="_blank">pull request</a>.
