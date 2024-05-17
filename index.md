---
layout: home
title: Unofficial VyOS Package Repository
---
Since the maintainers of the VyOS project have [decided](https://blog.vyos.io/community-contributors-userbase-and-lts-builds) that they won't permit external access to their own package repositories anymore, I've set up my own unofficial one.

### Using with `vyos-build`

Download the [public key](vyos-pkg.gpg) and put it in
`/etc/apt/keyrings/vyos-pkg.gpg`. You can achieve this with:

```
wget -qO- {{ site.url }}/vyos-pkg.asc | sudo tee /etc/apt/keyrings/vyos-pkg.asc >/dev/null
```

Then, run the `build-vyos-image` script from the [`vyos-build` repository](), passing the --vyos-mirror argument:

```
sudo ./build-vyos-image iso --architecture amd64 --build-by "j.randomhacker@vyos.io" --vyos-mirror "[signed-by=/etc/apt/keyrings/vyos-pkg.asc {{ site.url }}/deb"
```

Then run `apt update && apt install -y` followed by the names of the packages you want to install.

## How to contribute?

Please contribute changes and bug reports in the relevant repository above.

Have a security issue? Please email [Matthew](mailto:matthew@kobayashi.au) with details.

Have your own action? Please create a 
[pull request on this repository]({{ site.url }}/pulls).
