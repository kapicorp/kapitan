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

## Update documentation

We use [mkdocs](https://www.mkdocs.org/) to generate our gh-pages from `.md` files under docs/ folder.

Updating our gh-pages is therefore a two-step process.

### Update the markdown

Submit a PR for our master branch that updates the `.md` file(s). Test how the changes would look like when deployed to gh-pages by serving it on localhost:

`make local_serve_documentation`

### Submit a PR

Once the above PR has been merged, use `mkdocs gh-deploy` command to push the commit that updates the site content to your own gh-pages branch. Make sure that you already have this gh-pages branch in your fork that is up-to-date with our gh-pages branch such that the two branches share the commit history (otherwise Github would not allow PRs to be created).

```text
# locally, on master branch (which has your updated docs)
COMMIT_MSG="your commit message to replace" make mkdocs_gh_deploy
```

After it's pushed, create a PR that targets our gh-pages branch from your gh-pages branch.