# Changelog

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Extended Kibana dashboard for rasdaemon with panels that show just errors.
- Kibana dashboard to show heartbeat losses.

### Changed
- Invoke ``check_hsn_cables.py`` without specifying Python 2.

### Fixed
- Man page for ``sat diag`` updated to state explicitly what devices it can
  be applied to.
- Man page for ``sat showrev`` updated to describe the release directory and
  provide an example of products output.
- Restored certificate-nonvalidation warning circumvention from ``sat diag``,
  ``sat linkhealth``, and ``sat sensors``.

## Removed
- Removed "flow_control_config" field from ``sat linkhealth``. It is no longer
  present in Redfish, by design.

## [2.0.0] - 2020-05-06

### Added
- ``sat sensors`` supports ``--types`` for BMC types.
- ``sat sensors`` handles ``--xnames`` consistenty with ``sat linkhealth``.
- ``sat diag`` supports shared ``--redfish-username`` option.
- ``sat cablecheck`` supports ``check_hsn_cables.py``'s options.
- Ability to list drives in ``sat hwinv`` with ``--list-drives``.
- Ability to list CMM rectifiers in ``sat hwinv`` with ``--list-cmm-rectifiers``
- New fields for drive counts and total drive capacity when listing and
  summarizing nodes in ``sat hwinv``.
- New `--show-empty` and `--show-missing` options to allow override of default
  behavior to hide columns that are all EMPTY or MISSING.
- ``sat switch`` command for automation of switch enable/disable during
  switch replacement.
- ``sat k8s`` command which currently shows replica pods spun up on the
  same node.

### Changed
- Default behavior when printing tables is now to hide columns when values for
  those columns are either all EMPTY or all MISSING. The default behavior can be
  overridden using the `--show-empty` and `--show-missing` options.
- Man page of ``sat sensors`` revised to be more explicit with respect to
  supported BMC types and for style consistency.
- Errors in ``sat sensors`` changed to be less confusing. The xname is
  included in query errors and the "unable to identify" error is omitted
  if one of these errors is logged.
- Man page of ``sat diag`` revised to better cover interactive mode.
- Showrev will no longer exit at the first failure to retrieve a set of
  information. E.g., a failure to retrieve package version info will not impact
  showrev's ability to display system revision information.
- Improved sitefile handling by ``sat setrev`` to create directory and better
  detect and warn if file does not appear to be as expected.
- Included username in warning for failure to authenticate with token.
- Moved Redfish indication in user/password prompt to left side of colon.
- ``sat hwinv`` now reports memory in GiB rounded to 2 places.
- Changed project license from Cray Proprietary to MIT license and added notices
  to all source files.
- Implementation of ``processor_count`` property of ``Node`` objects now counts
  ``Processor`` objects instead of relying on 'LocationInfo' field in HSM.

### Removed
- Removed ``--substr`` option from ``sat showrev``, the effect of which can
  be accomplished using the general ``--filter`` option instead.
- Removed certificate-nonvalidation warning circumvention from ``sat diag``,
  ``sat linkhealth``, and ``sat sensors``. Occurrence of this warning is no
  longer normal behavior.

### Fixed
- Build version in ``sat showrev`` is now read from the ``/etc/cray-release``
  file and the field now reads "Release version".
- Slurm version now checked via pod.

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
