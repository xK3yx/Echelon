# Repository conventions

Working notes for anyone (human or AI) contributing to this repository.

## Authorship

- All commits are authored by **xK3yx**.
- **Do not add `Co-Authored-By:` trailers**, AI attribution lines, or generated-with footers to commit messages.
- Local git config should be:
  - `user.name = xK3yx`
  - `user.email = 58119332+xK3yx@users.noreply.github.com`

## Commit messages

Use plain conventional commits — no AI markers anywhere:

- `feat:` — new user-facing functionality
- `fix:` — bug fix
- `docs:` — documentation only
- `chore:` — tooling, configs, deps
- `refactor:` — code restructure with no behaviour change
- `test:` — adding or updating tests

A short subject line, optional body explaining the *why*. No footers other than the conventional `BREAKING CHANGE:` when applicable.

## Documentation

Public-facing docs (README, repository description, social previews) describe the project as a refined version of a Diploma in Information Technology final-year project. Keep the academic origin generic — do not name the institution, city, or country.
