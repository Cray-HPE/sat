# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2020-03-27

### Added
- Kibana dashboard for AER messages.
- Kibana dashboard for rasdaemon messages.

### Changed
- Kibana kernel dashboards to use DSL from KQL.
- Put list of subcommands in usage help in alphabetical order.
- All Kibana dashboards include time, hostname, message, and severity columns in
  the search output.

### Fixed
- The regular expression for the Kibana LBUG search query has been corrected.
- The output of firmware subcommand now properly sorts xnames by their numerical
  components.

## [1.1.0] - 2020-03-18

### Added
- Kibana dashboards for kernel-related error messages.
- A kibana dasbhoard for viewing nodes set admindown and Application Task
  Orchestration and Management (ATOM) test failure log messages in the system
  monitoring framework.
- ``contains_component`` method added to ``XName`` class to test whether a
  component represented by an xname contains another.
- New ``--products`` option for ``sat showrev`` that shows information about
  installed product versions from ``/opt/cray/etc/release`` directory.

### Changed
- The xnames specified with the ``--xnames`` or ``--xname-file`` options are
  now made unique while preserving order.

### Fixed

- Fixed sorting by xname in output of ``sat status``.
- Made ``sat status`` more robust when keys are missing from data returned by
  HSM API.
- Fixed boolean operator precedence in filtering queries.
- Fixed exception that occurred in ``sat sensors`` when trying to split a list
  of xnames on commas or to iterate over None.
- Fixed ``sat showrev`` traceback that resulted from ``/opt/cray/etc/release``
  being changed from a file to a directory.

## [1.0.0] - 2020-02-27

This is the version at which we started properly maintaining our version
number.

### Added

- CHANGELOG.md in a simple markdown format.

## [0.0.3] - 2020-02-26

This is the version prior to the version at which we started properly maintaining
our version number.

### Added

- A sat command and all its subcommands, including sensors, firmware, diag,
  hwinv, cablecheck, setrev, auth, hwmatch, linkhealth, status, and showrev.
- A Jenkinsfile and spec file to build sat as an rpm.
- An Ansible role that installs sat within the crayctl ansible framework.
- A kibana dasbhoard for viewing MCE log messages in the system monitoring
  framework.
