---
layout: home
title: Unofficial VyOS `circinus` Package Repository
---
Since the maintainers of the VyOS project have [decided](https://blog.vyos.io/community-contributors-userbase-and-lts-builds) that they won't permit external access to their own package repositories anymore, I've set up my own unofficial one.

### Using with `vyos-build`

Run the `build-vyos-image` script from the [`vyos-build` repository](https://github.com/vyos/vyos-build/blob/current), passing the --vyos-mirror argument:

```
sudo ./build-vyos-image iso --architecture amd64 --build-by "j.randomhacker@vyos.io" --vyos-mirror "[trusted=yes] {{ site.url }}/vyos-pkg/circinus/deb"
```

## How to contribute?

Please contribute changes and bug reports in the relevant repository above.

Have a security issue? Please email [Matthew](mailto:matthew@kobayashi.au) with details.

Have your own action? Please create a [pull request on this repository](https://mattkobayashi.github.io/vyos-pkg.github.io/pulls).
