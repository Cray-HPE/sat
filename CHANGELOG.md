# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- ``sat cablecheck`` supports shared ``--redfish-username`` option.
- ``sat cablecheck`` supports ``check_hsn_cables.py``'s options.
- Ability to list drives in ``sat hwinv`` with ``--list-drives``.
- New fields for drive counts and total drive capacity when listing and
  summarizing nodes in ``sat hwinv``.

### Changed
- Man page of ``sat diag`` revised to better cover interactive mode.
- Showrev will no longer exit at the first failure to retrieve a set
  of information.
  E.g., a failure to retrieve package version info will not impact showrev's
  ability to display system revision information.

## [1.3.0] - 2020-04-09

### Added
- Added ``Class`` to the fields reported by ``sat status``.
- ``--snapshots`` option for sat firmware.

### Changed
- Revised man pages for improved style and consistency.
- Changed ``sat linkhealth`` to display ``flow_control_config`` rather than
  ``flow_control_configuration`` as a column heading.
- Changed dependency from slingshot-cable-validation to slingshot-tools.

### Removed
- Removed unsupported ``--xname`` option from ``sat status`` man page.

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

## [1.1.2] - 2020-03-25

### Fixed
- Updated ``setup.py`` to not include our ``tools`` python package and
  subpackages of our ``tests`` package.

## [1.1.1] - 2020-03-20

### Changed
- Changed ``sat linkhealth`` to target switches contained by specifed xnames,
  for example xname component x1000c1 contains xname component x1000c1s2b0, as
  does x1000c1s2b0 (an xname component contains itself).

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
