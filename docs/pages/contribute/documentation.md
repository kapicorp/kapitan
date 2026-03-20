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

We use [mkdocs](https://www.mkdocs.org/) to build the site content and
[mike](https://github.com/jimporter/mike) to manage versioned documentation on
`gh-pages`.

Updating our gh-pages is therefore a two-step process.

### Update the markdown

Submit a PR for our master branch that updates the `.md` file(s). Test how the
changes look locally before sending the PR:

1. Run `make docs_serve`
2. Open [`http://localhost:8000`](http://localhost:8000)
3. If port `8000` is already in use, override it:

   ```bash
   make docs_serve DOCS_DEV_ADDR=localhost:8001
   ```

### Submit a PR

Once the above PR has been merged, our CI will deploy your docs automatically.
