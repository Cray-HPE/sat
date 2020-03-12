# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Kibana dashboards for kernel-related error messages.
- A kibana dasbhoard for viewing nodes set admindown and Application Task
  Orchestration and Management (ATOM) test failure log messages in the system
  monitoring framework.

### Fixed

- Fixed sorting by xname in output of ``sat status``.
- Made ``sat status`` more robust when keys are missing from data returned by
  HSM API.
- Fixed boolean operator precedence in filtering queries.
- Fixed exception that occurred in ``sat sensors`` when trying to split a list
  of xnames on commas or to iterate over None.

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