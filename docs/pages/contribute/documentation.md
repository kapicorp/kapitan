---
comments: true
tags:
  - community
---
# :kapitan-logo: Documentation

Our documentation usully prevents new users from adopting **Kapitan**. Help us improve by contributing with fixes and keeping it up-to-date.

## Articles

Write articles on Kapitan and share your way of working. Inspire others, and reach out to have your article published / endorsed by us.

## This Website

Find something odd? Let us know or change it yourself: you can edit pages of this website on Github by clicking the pencil icon at the top right of this page!

## Update documentation [![Build and deploy documentation](https://github.com/kapicorp/kapitan/actions/workflows/documentation.yml/badge.svg)](https://github.com/kapicorp/kapitan/actions/workflows/documentation.yml)

We use [mkdocs](https://www.mkdocs.org/) to generate our gh-pages from `.md` files under docs/ folder.

Updating our gh-pages is therefore a two-step process.

### Update the markdown

Submit a PR for our master branch that updates the `.md` file(s). Test how the changes would look like when deployed to gh-pages by serving it on localhost:

1. Edit the `strict` property in `mkdocs.yml` and set it to `false`.
2. `make local_serve_documentation`
3. Now the documentation site should be available at [`localhost:8000`](http://127.0.0.1:8000).

### Submit a PR

Once the above PR has been merged, our CI will deploy your docs automatically.
