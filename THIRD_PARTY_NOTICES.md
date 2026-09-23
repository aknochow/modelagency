# Third-party notices

## PatternFly foundation stylesheet

`site/assets/css/patternfly-base.css` is vendored from the public
[FlyDocs repository](https://github.com/aknochow/flydocs), source commit
[`6e0c6fc01ed5f29f62d8fde313378c91d492b007`](https://github.com/aknochow/flydocs/commit/6e0c6fc01ed5f29f62d8fde313378c91d492b007).
FlyDocs is distributed under Apache License 2.0. The corresponding license
text is retained in [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt).

The stylesheet provides PatternFly v6 design tokens and theme definitions,
including [Project Felt](https://www.patternfly.org/design-foundations/theming/).
PatternFly is an open source Red Hat project; see the [PatternFly site](https://www.patternfly.org/),
[repository](https://github.com/patternfly/patternfly), and its
[Apache-2.0 license](https://github.com/patternfly/patternfly/blob/main/LICENSE).
modelagency's dashboard-specific CSS is in `site/styles.css` and uses the
vendored semantic tokens. No FlyDocs templates, JavaScript, documentation
content, or logos are included.

## Harbor Terminal-Bench aggregate results

The normalized Terminal-Bench adapter uses aggregate leaderboard facts from
the [Harbor Terminal-Bench leaderboard](https://hub.harborframework.com/datasets/terminal-bench/terminal-bench/latest?tab=leaderboard&leaderboard=4-0-0).
The benchmark source repository is available at
<https://github.com/harbor-framework/terminal-bench> and is licensed under
the [Apache License 2.0](https://github.com/harbor-framework/terminal-bench/blob/main/LICENSE).
modelagency does not redistribute Terminal-Bench task content, solutions,
trajectories, or raw evaluation artifacts.
