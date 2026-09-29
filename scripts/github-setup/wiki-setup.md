# GitHub Wiki setup and maintenance

The repository's Wiki setting was verified as enabled through GitHub's public API. Its separate Git repository was not accessible when checked; first-page initialization and publication are pending. No live pages are claimed yet.

## Initialize once

Open the [repository Wiki](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki) while signed in with write access. Choose **Create the first page**, keep the title **Home**, enter temporary text and save. The maintained Home page will replace that temporary text on publication. See [GitHub's Wiki instructions](https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages).

## Preview and publish

Run from the main repository with Python 3.11+, Git and existing authorized SSH access:

```sh
python3 scripts/check_docs.py
python3 scripts/check_repository.py
python3 scripts/publish_wiki.py
python3 scripts/publish_wiki.py --apply
```

The publisher clones the Wiki into a temporary directory, copies the ten maintained Markdown files from `docs/wiki/`, and lists changes. Only `--apply` commits and pushes. Identical content produces no new commit. Unrelated Wiki pages are preserved; concurrent remote changes cause a normal push rejection rather than a force push. The temporary clone is removed afterward. Existing configured Git identity is used without printing credentials or contact information.

## Ownership

Edit maintained navigation pages in `docs/wiki/` and publish after review. These pages link to the detailed documents in the main repository, so design, testing and course evidence have one authoritative location. Direct edits to a maintained Wiki page will be replaced by the next publication; bring intended edits back into its source file first.

After publishing, verify Home, the sidebar and topic links in GitHub. Update README and the human-action checklist to record actual publication. Future Wiki navigation changes need an explicit publisher run; no automatic synchronization or extra token has been configured.
