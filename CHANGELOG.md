# Changelog

(C) Copyright 2020-2025 Hewlett Packard Enterprise Development LP

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
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.34.4] - 2025-02-25

### Security
- Update the version of cryptography from 43.0.1 to 44.0.1 to resolve
  CVE-2024-12797, a low-severity dependabot alert.

## [3.34.3] - 2025-02-13

### Fixed
- Include name of snapshot created by `sat firmware` in INFO log message.

## [3.34.2] - 2025-02-07

### Fixed
- Added support for the `drop_branches` parameter in CFS v3 configurations.
  This allows CFS to drop branch names from the CFS layers after resolving
  them to commit hashes when creating or updating configurations.

## [3.34.1] - 2025-01-09

### Fixed
- Update the version of jinja2 from 3.1.4 to 3.1.5 to resolve
  CVE-2024-56201, and CVE-2024-56326

## [3.34.0] - 2025-01-08

### Changed
- Dropped the `Arch` field from `sat status` for all the components
  except for Node type.

## [3.33.9] - 2024-12-11

### Removed
- Removed internal default values for rootfs_provider{,passthrough} 
  from sat bootprep

## [3.33.8] - 2024-12-18

### Fixed
- Fixed a traceback that occurs in `sat swap blade` when the node classes
  reported by HSM includes both "Mountain" and "Hill" for a single blade.

## [3.33.7] - 2024-12-18

### Fixed
- Fixed the traceback error encountered during session checks in CFS v2
  when using a smaller page size.

## [3.33.6] - 2024-12-12

### Added
- Added support to new HSM Types, namely `CabinetPDU`, `CabinetPDUController`,
  `CabinetPDUPowerConnector` and `MgmtSwitch` in `sat status`

## [3.33.5] - 2024-12-11

### Fixed
- Fixed sorting warnings in `sat showrev`

## [3.33.4] - 2024-12-11

### Added
- Added support for using either the CFS v2 or v3 API in `sat bootsys`,
  depending on the value of the `--cfs-version` command-line option or the
  `cfs.api_version` config-file option.

## [3.33.3] - 2024-12-10

### Added
-  Added the ability to sort reports by multiple fields

## [3.33.2] - 2024-12-10

### Fixed
-  Added error message and system exit when token file is not found.

## [3.33.1] - 2024-12-02

### Fixed
- Fixed `sat bootprep` to include the value of `ims_require_dkms` in the created
  CFS configurations, even when explicitly set to `False`.

## [3.33.0] - 2024-11-25

### Added
- Added support for using either the CFS v2 or v3 API in `sat bootprep`,
  depending on the value of the `--cfs-version` command-line option or the
  `cfs.api_version` config-file option.

### Changed
- The `sat bootprep` command defaults to using the v3 CFS API instead of v2.
- When using the CFS v3 API, CFS configuration layers defined in `sat bootprep`
  input files are required to specify the `playbook` field as this is required
  by the CFS v3 API.

## [3.32.13] - 2024-11-25

### Fixed
- Added validation to `sat bootprep` to verify that `rootfs_provider` and
  `rootfs_provider_passthrough` exist before checking for empty string values.

## [3.32.12] - 2024-11-21

### Fixed
- Fix sorting by product version in `sat showrev --products` to sort by semantic
  version rather than a simple lexicographic order.

## [3.32.11] - 2024-11-12

### Fixed
- Added validation to `sat bootprep` to prohibit empty strings in `rootfs_provider` and
  `rootfs_provider_passthrough` keys of `boot_sets`

## [3.32.10] - 2024-11-04

### Fixed
- Fix jinja2 rendering of `boot_sets` data in `sat bootprep`.

## [3.32.9] - 2024-10-29

### Fixed
- Fix missing CFS fields in `sat status` when using CFS v3.

## [3.32.8] - 2024-10-21

### Fixed
- Fix unused code in `get_config_value` for handling infinite BOS timeouts.

## [3.32.7] - 2024-10-15

### Fixed
- Remove the ability to read VCS password from a file which is no longer necessary in `sat bootprep`.

## [3.32.6] - 2024-10-08

### Changed
- Updated the version of `kubectl` included in `cray-sat` container to 1.24 to
  match the version of Kubernetes included in CSM 1.6.

## [3.32.5] - 2024-10-03

### Added
- Update the Python kubernetes version to the latest one supported in CSM 1.6

## [3.32.4] - 2024-09-27

### Added
- Add jinja rendering of rootfs_provider_passthrough value for the boot_set to create session
  template with iSCSI values.

## [3.32.3] - 2024-09-27

### Added
- Update man-page of `sat status`, `sat bootprep`, `sat bootsys` after introduction of
  CFS V2-V3.

### Security
- Update the version of cryptography from 42.0.4 to 43.0.1 to resolve
  CVE-2024-6119

## [3.32.2] - 2024-09-27

### Fixed
- Fixed for IUF stuck during `update-cfs-config` and `prepare-images` stage while
  executing `git ls-remote` fetching the credentials.

## [3.32.1] - 2024-09-17

### Changed
- Changed `sat bootprep` and `sat bootsys` to use the CFS.V2 updated classes from `csm-api-client`

## [3.32.0] - 2024-09-11

### Added
- Update `sat status` to support CFS v2 or v3 and have the latest version of `csm-api-client`

## [3.31.1] - 2024-09-02

### Changed
- Changed `sat bootsys` to enable default timeouts to infinite for BOS boot, shutdown, and reboot.

## [3.31.0] - 2024-08-21

### Fixed
- Updating the cray-product-catalog & python-csm-api-client to latest versions.

## [3.30.2] - 2024-08-14

### Fixed
- Log an error message and stop waiting on BOS sessions that have been deleted
  in the `bos-operations` stage of `sat bootsys`.

## [3.30.1] - 2024-08-13

### Fixed
-  When the token used to access the API gateway is expired, log a helpful error
  message instructing the user to reauthenticate with `sat auth` and then exit
  instead of printing a traceback and exiting.

## [3.30.0] - 2024-08-09

### Changed
- When customizing images with `sat bootprep`, pass the desired image name
  directly to CFS when creating the image customization session, if supported by
  the version of CFS on the system. This improves the performance and
  reliability of `sat bootprep`.
- Update to a new version of the `csm-api-client` that allows querying the CFS
  version from the CFS API.
- Update to version 3.0.2 of the `semver` package. The only breaking change
  appears to be related to supported Python versions, but it should not affect
  SAT.

## [3.29.2] - 2024-08-06

### Changed
- Modify `sat bootsys boot --stage ncn-power` to boot the master nodes (other than `ncn-m001`)
  and the worker nodes at the same time.

## [3.29.1] - 2024-08-02

### Fixed
- Fixed a logging issue with messages logged by the `waiting` module used in
  `sat bootsys` and other commands, so that log messages emitted by this module
  are correctly handled and formatted.

## [3.29.0] - 2024-08-01

### Changed
- Removed the step that freezes Ceph from the `platform-services` stage of `sat bootsys shutdown`
- Modified the `ncn-power` stage of `sat bootsys shutdown` to shut down the NCNs
  one group at a time instead of all simultaneously. The new order of this stage
  is to shut down workers, shut down masters (except ncn-m001), unmount all Ceph
  and s3fs filesystems on `ncn-m001`, unmount and unmap all RBD devices on
  `ncn-m001`, and then shut down storage nodes.
- Disable the `ensure-ceph-mounts` systemd cron job on `ncn-m001` during the `ncn-power` stage
  of `sat bootsys shutdown`. Then, re-enable it during the `ncn-power` stage of
  `sat bootsys boot`.
- Modified the `sat bootsys platform services` stage to not perform unfreeze ceph
- Updated the power on order of node groups in `sat bootsys ncn-power` stage to storage,
  unfreezing of ceph, managers and then the worker nodes.
- Added a wait on the Kubernetes API being reachable between the step that starts
  kubelet and the step that re-creates Kubernetes cronjobs in the
  `platform-services` stage of `sat bootsys boot`.
- Added a function to mount `fuse.s3fs` and `ceph` post ceph health status check on `ncn-m001` in
  `ncn-power` stage of `sat bootsys boot`.
- Automate the procedure to stop containers until all containers are stopped in the
  `platform-services` stage of `sat bootsys shutdown`.
- Adding PG_NOT_DEEP_SCRUBBED in allowable checks excluded during ceph health check as it is
  ignorable.
- Automate the procedure of setting next boot device to disk before the management nodes are
  powered off as part of the full-system shutdown.
- Adding a ceph health check bypass prompt to take input from user and act accordingly.
  unfreezing of ceph would be done, only the wait period will be skipped if user wishes to.
- Improved logic in `cabinet-power` stage of `sat bootsys boot` to more reliably
  determine when a Job has been scheduled for the `hms-discovery` Kubernetes
  CronJob after it has been resumed.
- Remove unreliable step from the `platform-services` stage of `sat bootsys
  boot` that checked for Kubernetes CronJobs that were not being scheduled due
  to missing too many start times. The problem this attempted to solve should no
  longer occur with the CronJobControllerV2 being the default starting in
  Kubernetes 1.21.
- Changed the missing host key policy used with Paramiko in sat bootsys to the AutoAddPolicy to
  reduce warning messages displayed to the user.
- Automate the steps to recreate the /var/opt/cray/sdu/collection symbolic link to point at
  the `collection-mount` location where the `fuse.s3fs` filesystem is mounted.

### Fixed
- Updated `sat bootsys` to increase the default management NCN shutdown timeout
  to 900 seconds.
- Updated `sat bootsys` to include a prompt for input before proceeding with
  hard power off of management NCNs after timeout.
- addressed the bug to import time to make the sleep time effective before retrying to create
  cronjobs

## [3.28.12] - 2024-07-15

### Fixed
- Fixed a traceback that occurs during the `bos-operations` stage of `sat
  bootsys` if the BOS API fails to create a BOS session.
- Fixed the prompt in the `bos-operations` stage of `sat bootsys shutdown` and
  `sat bootsys reboot` to say "nodes" rather than "compute nodes and UANs",
  which is not always accurate.

## [3.28.11] - 2024-07-09

### Security
- Update the version of certifi from 2023.7.22 to 2024.7.4 to address CVE-2024-39689

## [3.28.10] - 2024-07-04

### Security
- Update the version of requests from 2.31.0 to 2.32.2 to address CVE-2024-35195
- Update the version of urllib3 from 1.26.18 to 1.26.19 to address CVE-2024-37891

## [3.28.9] - 2024-07-04

### Security
- Update the version of jinja2 from 3.1.3 to 3.1.4 to address CVE-2024-34064

## [3.28.8] - 2024-07-03

### Fixed
- Fixed issue in `sat status` to limit SLS query to only node-type components,
  which is the only component type where SLS data is used.

## [3.28.7] - 2024-06-26

### Fixed
- Improve info messages logged by `sat bootsys` in the `bos-operations` stage to
  use more precision when displaying percent successful values in order to avoid
  prematurely reporting that a BOS session is 100% complete when the actual
  percentage is between 99 and 100%.

## [3.28.6] - 2024-06-10

### Fixed
- Fixed issue where `sat status` made unnecessary queries to BOS, CFS, and SLS
  APIs when types other than `Node` were specified.

## [3.28.5] - 2024-05-31

### Added
- Add new HSM types, namely `NodeBMC`, `RouterBMC`, `MgmtSwitch`, `CabinetPDU` and
  `CabinetPDUPowerConnector` to `sat hwinv`. Also update the man page appropriately.

## [3.28.4] - 2024-05-08

### Fixed
- Polling the snapshot in `sat firmware` resulted in HTTP errors in large clusters.
  Hence, adding the retry option when it consecutively fails for up to 5 times.
- Remove expiration time and add `--delete-snapshot` option to delete the snapshot
  if it is no longer needed. By default, log a message referring the user how to
  delete the snapshot.

## [3.28.3] - 2024-05-03

### Security
- Update the version of idna from 3.3 to 3.7 to address CVE-2024-3651

## [3.28.2] - 2024-04-25

### Fixed
- Fix the `kubernetes` Python client library version to match the Kubernetes
  cluster version in CSM 1.5 and currently in CSM 1.6.

## [3.28.1] - 2024-04-10

### Added
- Updated the man page to include description of the new options implemented
  for `sat bmccreds`.

## [3.28.0] - 2024-04-09

### Deprecated
- Deprecate the `sat swap switch`, `sat swap cable`, and `sat switch` commands
  and log a message referring the user to the Slingshot Orchestrated Maintenance
  procedure instead. Prompt the user if they would still like to continue with
  the given `sat` command.

## [3.27.18] - 2024-04-05

### Fixed
- Improved the build of `python-csm-api-client` to take less time by
  adding `poetry.lock` file that resolves the dependencies.

## [3.27.17] - 2024-04-01

### Fixed
- Updated `generate_docs_tarball` to pass the correct log message in
  `sat bootprep generate-docs` to output the relative path as given by the user.

## [3.27.16] - 2024-03-28

### Fixed
- Update the `_update_container_status` method of the
  CFSImageConfigurationSession class in csm_api_client.service.cfs to handle
  the case when either `init_container_statuses` or `container_statuses` or
  both are None.

## [3.27.15] - 2024-03-27

### Changed
- Updated `begin_image_configure` to pass session name generated to address the
  sat bootprep incorrect logging of 2 session names

## [3.27.14] - 2024-03-27

### Changed
- Remove the restrictions on the passwords that can be set with `sat bmccreds`
  to allow for more complex passwords.
- Improve the password generation logic in `sat bmccreds` to support generating
  more complex passwords.

## [3.27.13] - 2024-03-25

### Updated
- Updated the default grace period of the `HMSDiscoveryScheduledWaiter` to 3
  minutes to allow more time for a new job to be scheduled by the cronjob.

## [3.27.12] - 2024-03-14

### Added
- Added support for the Power Control Service (PCS). Functionality using CAPMC
  was changed to use PCS instead.

## [3.27.11] - 2024-02-28

### Fixed
- Fixed for `sat showrev` to stop supporting `--release-files` option
  and log a warning message indicating that this option is no longer supported.

## [3.27.10] - 2024-02-26

### Added
- Update the man-page of `sat status` providing descriptions to all the parameters.

## [3.27.9] - 2024-02-22

### Security
- Update the version of cryptography from 42.0.2 to 42.0.4 to resolve
  CVE-2024-26130

## [3.27.8] - 2024-02-20

### Security
- Update the version of cryptography from 42.0.0 to 42.0.2 to resolve
  CVE-2024-0727

## [3.27.7] - 2024-02-20

### Changed
- Changed the WARNING messages about the deleted BOS sessions to DEBUG messages
  for `sat status`
- Changed the "Most Recent Image" column to show the IMS image ID instead of
  image name for `sat status`

## [3.27.6] - 2024-02-16

### Fixed
- Remove unnecessary queries to BOS to get the name of the session template for
  every single node component in the output of `sat status`.

## [3.27.5] - 2024-02-07

### Security
- Update the version of cryptography from 41.0.6 to 42.0.0 to resolve
  CVE-2023-50782

## [3.27.4] - 2024-02-06

### Security
- Update the version of jinja2 from 3.0.3 to 3.1.3 to address
  CVE-2024-22195

## [3.27.3] - 2024-01-31

### Fixed
- Fixed `sat swap switch` and `sat swap cable` so that they preserve all
  existing port policies applied to the ports on a switch or a cable across the
  disable and enable actions. The old behavior was that only the first policy
  would be preserved, which was a problem for ports with multiple policies
  configured.

## [3.27.2] - 2024-01-16

### Fixed
- Fixed a lengthy traceback that occurs when logging parsing errors that occur
  during parsing of `--filter` options.
- Fixed `--filter` option parsing to allow unquoted special characters (like the
  dash, for example) on the right-hand side (value) of a comparison.

## [3.27.1] - 2024-01-05

### Security
- Update the version of paramiko from 2.11.0 to 3.4.0 to address
  CVE-2023-48795

## [3.27.0] - 2023-12-05

### Added
- Added the ability to specify `additional_inventory` when creating CFS
  configurations with `sat bootprep`.

## [3.26.2] - 2023-12-01

### Security
- Update the version of cryptography from 41.0.4 to 41.0.6 to address
  CVE-2023-49083

## [3.26.1] - 2023-11-27

### Security
- Update the version of urllib3 from 1.26.17 to 1.26.18 to address
  CVE-2023-45803

## [3.26.0] - 2023-10-24

### Changed
- Added publishing of `cray-sat` container image to `csm-docker` in Artifactory
  as well as `sat-docker`. This is more consistent with other CSM builds.

## [3.25.6] - 2023-10-18

### Fixed
- Fixed `sat bootprep` to ensure image architecture is retained when customizing
  IMS images.

## [3.25.5] - 2023-10-12

### Security
- Update the version of urllib3 from 1.26.8 to 1.26.17 to address
  CVE-2023-43804.
- Update the version of cryptography from 41.0.3 to 41.0.4 to address
  a low-severity dependabot alert.

## [3.25.4] - 2023-09-01

### Fixed
- Update `sat showrev` to log a warning and proceed to display other system
  revision information when S3 credentials are not configured.
- Update `sat setrev` and `sat bootsys` to handle missing S3 credentials more
  gracefully.

## [3.25.3] - 2023-08-31

### Fixed
- Fixed a build issue which occurred when trying to get the kubectl version
  from the `metal-provision` repo.

## [3.25.2] - 2023-08-07

### Security
- Update the version of cryptography from 41.0.0 to 41.0.3 to address
  CVE-2023-38325.
- Update the version of pygments from 2.11.2 to 2.15.0 to address
  CVE-2022-40896.
- Update the version of certifi from 2022.12.7 to 2023.7.22 to address
  CVE-2023-37920.

## [3.25.1] - 2023-08-01

### Fixed
- Update PyYAML to 6.0.1 and csm-api-client to 1.1.5 to resolve build issues.

## [3.25.0] - 2023-06-26

### Added
- Added support for specifying new DKMS special parameter in CFS configuration
  layers created by `sat bootprep`

## [3.24.0] - 2023-06-23

### Added
- Added support for multiple architectures to `sat bootprep`, which includes the
  following:
    - The ability to filter the base image or recipe from a product based on the
      architecture of the image or recipe in IMS
    - The ability to combine multiple base image or recipe filters when
      specifying a base image from a product
    - The ability to specify the architecture for each boot set in a BOS
      session template

### Changed
- Changed docker image build to query lts/csm-1.5 branch of metal-provision
  repo for the kubectl version to use in the cray-sat container.

### Fixed
- Fixed extreme slowness with the `sat bootsys shutdown --stage
  platform-services` command when a large SSH `known_hosts` file is in use.

### Changed
- Changed the `bos-operations` stage of `sat bootsys` to no longer check
  whether BOS session templates need an operation performed before creating a
  BOS session. BOS will handle ensuring idempotency instead.

### Security
- Update the version of cryptography from 39.0.1 to 41.0.0 to address
  CVE-2023-2650.
- Update the version of requests from 2.27.0 to 2.31.0 to address
  CVE-2023-32681.

## [3.23.0] - 2023-06-08

### Added
- Added functionality to `sat bootsys boot --stage platform-services` to
  automatically recreate all Kubernetes cronjobs which are not being scheduled
  due to missing too many scheduled start times.
- Added functionality to `sat bootsys boot --stage cabinet-power` to
  automatically recreate the `hms-discovery` cronjob if it fails to be
  scheduled on time.
- Added support for multitenancy, which can be configured with the
  `api_gateway.tenant_name` config file option and `--tenant-name` command line
  option.

### Fixed
- Fixed an unnecessary CAPMC API request and a confusing warning message during
  `sat bootsys shutdown --stage cabinet-power` when there are no non-management
  nodes in air-cooled cabinets.

### Changed
- Improved the check procedure to determine whether the `hms-discovery` cronjob
  has been scheduled during the `cabinet-power` stage of `sat bootsys`, as well
  as the `sat swap blade` subcommand.
- Update the hms-discovery cronjob manipulation functionality to use the
  BatchV1 Kubernetes API instead of the BatchV1beta1 API.

## [3.22.0] - 2023-05-08

### Added
- Added ability to filter images provided by a product using a wildcard pattern
  to specify the base input image in a `sat bootprep` input file
- Added a `cert_verify` parameter to the `s3` section of the configuration file.

### Changed
- Changed logging in `sat bootsys` such that all sessions will have a logging
  message printed at the end of the `sat bootsys` run. BOS sessions with
  greater than 0% failed components will be logged as warning messages, and all
  other session statuses will be logged as info messages.
- Changed the default value of the config file option `bos.api_version` to "v2".
- Modified logging for SAT such that multi-line log messages will now be logged
  with consistent formatting for each line.
- Updated unit test infrastructure to use `nose2`.
- Reduced the number of log messages when insecure HTTPS requests are made.
- Update the version of `csm-api-client` to 1.1.4 to simplify loading of the
  Kubernetes configuration when running in a container inside the cluster and
  remove code duplication.

### Fixed
- Fixed a bug in the `bos-operations` stage of `sat bootsys` where a Bad Request
  error could appear in the output when checking node states.
- Fixed a bug where the `bos-operations` stage of `sat bootsys` would not correctly
  wait for a shutdown or boot operation to complete with BOS v1 and certain versions
  of the `kubectl` command.
- Fixed a bug where the `bos-operations` stage of `sat bootsys` did not report
  staged sessions as complete if the sessions did not apply to any components
  due to a `--bos-limit` parameter that did not overlap with the components in the
  session template.
- Fixed a bug which caused the wrong container name to be logged when a CFS
  image customization failed in newer versions of CSM.
- Updated container build script to pull in the correct kubectl version from the
  metal-provision repository instead of the csm-rpms repository.

### Removed
- Removed support for CRUS.

### Security
- Update the version of oauthlib from 3.2.1 to 3.2.2 to resolve a moderate
  dependabot alert for CVE-2022-36087.
- Update the version of cryptography from 36.0.1 to 39.0.1 to address
  CVE-2023-23931.
- Rebuilt the cray-sat container image to address CVE-2023-27536 in
  curl/libcurl present in the cray-sat:3.21.4 container image.

## [3.21.2] - 2023-02-13

### Fixed
- Updated `csm-api-client` library version to fix authentication with `sat auth`
  for new tokens.

## [3.21.1] - 2023-01-30

### Fixed
- Fixed missing `--bos-boot-timeout` and `--bos-shutdown-timeout` options
  for `sat bootsys reboot`.

## [3.21.0] - 2023-01-27

### Changed

- Removed the "active" field from the output of `sat showrev`.

### Fixed
- Fixed a bug in which `sat firmware` would fail with 400 Bad Request errors.
- Fixed a bug in which API requests were not being logged.

### Added
- Added the `--staged-session` option to `sat bootsys` which can be used to
  create staged BOS sessions.
- Added descriptions for `--bos-limit` and `--recursive` to the `sat bootsys`
  man page.
- Added ability to filter the images provided by a product using a prefix when
  specifying the base of an image in a `sat bootprep` input file.
- Added support for hyphenated product names in `sat bootprep` variables.

## [3.20.0] - 2022-01-13

### Added
- Added new command `jobstat`, which provides system-wide view of application
  status data.
- Added a `sat bootprep list-vars` subcommand which lists the variables
  available in bootprep input files at runtime.
- Added a `sat bootsys reboot` subcommand which uses BOS to reboot nodes.
- Added a report to the output of `sat bootprep` which describes the
  configurations, images, and session templates which were created during the
  bootprep run.
- The value of the `playbook` property of CFS configuration layers in `sat
  bootprep` input files can now be rendered with Jinja2 templates.
- Added a new `--limit` option to `sat bootprep run` that allows limiting which
  types of items from the input file are created.

### Changed
- Refactored to use common `APIGatewayClient`, `CFSClient`, `HSMClient`, and
  `VCSRepo` classes and associated exception classes and utility functions from
  the new `csm-api-client` Python library.
- New common functionality in `csm-api-client` is now used to differentiate 404
  errors to provided better error messages and clearer semantics in `sat swap
  blade` and `sat bootprep`.
- `sat bootprep` now prompts individually for each CFS configuration that already
  exists.
- Improved output when creating CFS configurations and BOS session templates with
  `sat bootprep`.

### Fixed
- Fixed a bug which prevented `sat init` from creating a configuration file in
  the current directory when not prefixed with `./`.
- Updated `csm-api-client` dependency to version 1.1.0 to fix minor type
  checking bug with `APIGatewayClient.set_timeout()`.
- Fixed a bug in which `sat status` would fail with a traceback when using
  BOS v2 and reporting components whose most recent image did not exist.
- Improved the performance of `sat status` when using BOS v2.
- Fixed a build issue where the `sat` container could contain a
  different version of `kubectl` than is found in CSM.
- Added missing description of the `--dry-run` option to `sat bootprep` man
  page, and clarified its help text.
- Corrected the man page description of the `--save-files` option to say that
  BOS session templates will be saved in dry-run mode, though they may be
  incomplete. Slightly reworded the help text for `--save-files`.

### Security
- Update the version of certifi from 2021.10.8 to 2022.12.7 to resolve a
  medium-severity dependabot alert.

## [3.19.3] - 2022-09-29

### Changed
- Updated the README file to remove outdated information.
- Removed the HTTP timeout from the IMSClient instance used in
  `sat bootprep` to address slow IMS delete requests.

### Removed
- Removed the `cray-sat` spec file from the repository.

### Fixed
- Fixed an issue where `sat bootprep` would sometimes fail to rename
  large images.

### Security
- Update the version of oauthlib from 3.2.0 to 3.2.1 to address
  CVE-2022-36087.

## [3.19.2] - 2022-08-30

### Changed
- Changed the name of the VCS repository containing the `product_vars.yaml`
  file from `hpc-shasta-software-recipe` to `hpc-csm-software-recipe`.

## [3.19.1] - 2022-08-26

### Changed
- Reverted the default value of the config file option `bos.api_version` to "v1".
- Shasta Software Recipe version numbers now conform to Semantic Versioning
  syntax, and version comparisons to determine the latest version are now
  handled according to Semantic Versioning precedence rules.

### Fixed
- The ordering of the bootup sequence of management NCNs in the
  `sat-bootsys(8)` man page was fixed to reflect their correct ordering in the
  `ncn-power` stage of `sat bootsys boot`.
- Fixed a bug in which giving an invalid subcommand resulted in a traceback
  on Python 3.9.
- Fixed a bug in `sat bootprep` that caused dependent images to be skipped when
  an existing image that is used as the base of another image is skipped.

### Security
- Update the version of paramiko from 2.9.2 to 2.10.1 to mitigate
  CVE-2022-24302.

## [3.19.0] - 2022-08-16

### Added
- Added `--recipe-version`, `--vars-file`, and `--vars` options to `sat
  bootprep run` to specify variables for use in `bootprep` input files.
- Added variable substitution support to the following fields in `sat bootprep`
  input files:
	- `name` of elements of the `configurations` array
	- `name`, `branch`, and `version` of elements under `layers` in
	  elements of the `configurations` array
	- `name`, `base.product.version`, and `configuration` properties of
	  elements in the `images` array.
	- `name`, `configuration`, and `image` properties of elements in the
	  `session_templates` array.
- Defined a `sat bootprep` input file schema version and began validating the
  schema version specified by `sat bootprep` input files.
- Added functionality to `sat bootprep` to look up images and recipes provided
  by products.
- Added functionality to `sat bootprep` to allow session templates to refer to
  images by their `ref_name` under the new `image.image_ref` property.

### Changed
- Changed the `sat bootprep` input file schema by adding a new `base` property
  for an image and moved the existing `ims` property beneath that new property.
- Changed how `sat bootprep` determines dependencies between images in the input
  file using new `ref_name` and `base.image_ref` properties.
- Changed the default value of the config file option `bos.api_version` to "v2".

### Deprecated
- Specifying the `ims` property at the top level of an image in the `sat
  bootprep` input file is deprecated.
- Specifying a string value for the `image` property of session templates in the
  `sat bootprep` input file is deprecated.

## [3.18.0] - 2022-08-10

### Added

- Added information regarding the `--bos-version` command-line argument to man
  pages for relevant subcommands.
- Added a `sat swap blade` subcommand which partially automates the procedure
  for swapping compute and UAN blades.

### Changed
- Updated `sat bootsys` man page to reflect changes to stages and remove
  outdated information.

### Fixed
- Fixed unit tests that failed when run in PyCharm.

## [3.17.1] - 2022-07-05

### Changed
- Whenever `sat` is invoked, the permissions of the `~/.config/sat/sat.toml`
  file will be set to `0600`, and the permissions of the `~/.config/sat/tokens`
  and `~/.config/sat` directories will be set to `0700`.

### Fixed
- Fixed an issue where SAT crashed with a traceback if the file
  `/etc/opt/cray/site.yaml` existed but was empty. A warning message will now be
  logged instead.

## [3.17.0] - 2022-06-27

### Added
- Added client support for the BOS v2 API.
- Added a `--bos-version` command line option and `bos.api_version`
  configuration file option which can be used to specify which version of the
  BOS API to use.
- Added BOS v2 support to `sat bootprep`.
- Added BOS v2 support to `sat bootsys`.
- Added BOS v2 support to `sat status`, and added fields to `sat status` output
  listing the most recent BOS session, template, booted image, and boot status
  for nodes when BOS v2 is in use. Added a `--bos-fields` option to limit
  output to these fields.

### Fixed
- Fixed an issue causing `sat init` to not print a message when a new config was created.

### Removed
- Removed unused `docker` python package from requirements files.

### Changed
- Updated the project URL in `setup.py` to external GitHub location.
- Changed the format of the license and copyright text in all of the
  source files.

## [3.16.1] - 2022-06-07

### Fixed
- Fixed an issue in config-docker-sat.sh that was causing the builds to fail.

### Changed
- Changed builds to publish to the ``sat-docker`` Artifactory repository.

## [3.16.0] - 2022-05-31

### Changed
- Incremented the base version of Alpine used in the container image from 3.13
  to 3.15.
- Made changes related to the open sourcing of sat.
    - Update Jenkinsfile to use csm-shared-library.
    - Add Makefile for building container image.
    - Pull base container image from external location.
- Began using a separate ``cray_product_catalog`` package to query the product
  catalog in ``sat bootprep``.
- Began using a separate ``cray_product_catalog`` package to query the product
  catalog in ``sat showrev``.

### Fixed
- Fixed missing ``sat-hwhist`` man page.
- Fixed bug in ``sat status`` which caused a traceback when certain component
  state fields were missing in HSM.
- Fixed bug in ``sat status`` which caused a traceback when components were
  entirely missing from SLS.

## [3.15.1] - 2022-04-18

### Fixed
- Fixed tab completion in ``sat bash``.
- Fixed a bug with the ``$PATH`` environment variable not including the ``sat``
  executable in ``sat bash``.
- Fixed error reporting in ``sat firmware`` to treat responses containing the
  key "error" but an empty string for a value as non-errors.

## [3.15.0] - 2022-03-29

### Added
- Added a ``--bos-limit`` option to the  ``bos-operations`` stage of ``sat
  bootsys`` which passes the given limit string to the created BOS session.
  Also added a ``--recursive`` option to ``sat bootsys`` in order to allow
  specifying a slot or other higher-level component in the limit string.
- Added a ``--delete-ims-jobs`` option to ``sat bootprep run`` which causes
  successful IMS jobs to be deleted after ``sat bootprep`` is run. The default
  behavior was also changed to not delete jobs.
- Added information about nodes' CFS configuration status (desired
  configuration, configuration status, and error count) to ``sat status``.
- Added options to ``sat status`` to limit the output columns by specified
  CSM services. The added options are ``--hsm-fields``, ``--sls-fields``, and
  ``--cfs-fields``.
- Added a ``--bos-template`` option to ``sat status`` which allows the status
  report to be filtered by the specified session template's boot sets.

### Changed
- Changed the output of ``sat status`` to split different component types into
  different report tables.
- CFS image customization session container status logs in ``sat bootprep`` now
  automatically adjust space padding based on container name lengths.
- Added a stage to the Docker container build which runs ``pycodestyle`` on the
  SAT codebase and unit tests.

### Fixed
- Fixed ``sat bootprep`` to require the ``action`` positional argument.
- Fixed invalid reference to a FILES section in man page for ``sat bootprep``.

### Security
- Updated urllib3 dependency to version 1.26.5 to mitigate CVE-2021-33503, and
  refreshed Python dependency versions.

## [3.14.0] - 2022-02-24

### Added
- Added the ability to specify a commit hash in a product-based configuration
  layer in a ``sat bootprep`` input file.

### Changed
- The Dockerfile was reworked to leverage multistage builds and run unit tests
  in the same environment as the production container. The size of the container
  image has been cut in half as a result.
- Incremented the JSON Schema specification version for the ``sat bootprep``
  input file from draft-07 to 2020-12.
  in the same environment as the production container.

## [3.13.1] - 2022-01-26

### Added
- When ``--save-files`` is passed to ``sat bootprep``, BOS session template API
  request bodies will now be saved in addition to CFS configuration API request
  bodies.

### Fixed
- Improved ``sat bootprep`` to wait properly on CFS image configuration sessions
  to create the corresponding Kubernetes job before querying for pod status and
  to log helpful info messages when waiting on the job and pod.

## [3.13.0] - 2022-01-24

### Added
- Added a new subcommand, ``sat bootprep`` that automates creating CFS
  configurations, building and customizing IMS images, and creating BOS session
  templates which can be used to boot nodes in the system.

### Removed
- Removed password complexity checking from ``sat bmccreds`` due to incompatible
  open-source license.

## [3.12.1] - 2021-12-13

### Changed
- Bumped minor version to validate SAT after migration to internal HPE GitHub
  instance.

## [3.12.0] - 2021-12-07

### Changed
- Add a column to the output of ``sat showrev`` indicating when a product version
  is "active".

## [3.11.1] - 2021-11-22

### Changed
- Refactored `sat.apiclient` from a module into a subpackage.

## [3.11.0] - 2021-10-29

### Changed
- Added a ``--format`` option to ``sat xname2nid`` to set the output format
  to either 'range' or 'nid' for the node IDs.
- Added hostname information from SLS to `sat status` output.
- Added more information about unsuccessful API requests to the ``APIError``
  messages. This info is parsed from responses that use content type
  "application/problem+json" in their failure responses.

### Fixed
- Actions which wait on certain conditions (for example within ``sat bootsys``) will
  fail out more quickly when checking for the completion condition fails
  irrecoverably, instead of repeating a failing check until waiting times out.
- The ``ncn-power`` stage of ``sat bootsys`` will now only print one error
  message if ``impitool`` fails multiple times consecutively for a given
  component. If the number of failures for a given component exceeds 3, then
  that component will be marked as failed.
- Fixed the ``cabinet-power`` stage of ``sat bootsys`` to query CAPMC for power
  status of ComputeModules instead of the unsupported NodeBMC type.
- The ``cabinet-power`` stage of ``sat bootsys`` will now query CAPMC for chassis,
  compute modules, and router modules to power on or off individually instead of
  recursively in order to power on or off cabinets with disabled subcomponents.

## [3.10.0] - 2021-09-03

### Changed
- ``sat diag`` will now query HSM to verify that the components targeted for
  diagnostics are Rosetta switches.
- Changed sat to use the V2 HSM API.
- Changed ``sat xname2nid`` subcommand to translate slot, chassis, and cabinet
  xnames to node IDs in addition to node and node BMC xnames.

### Fixed
- Improved error handling of missing or empty FRUID key in system component data.
- The Ceph health timeout in the ``platform-services`` stage of ``sat bootsys boot``
  was changed to 60 seconds, from 600 seconds previously.
- If waiting for Ceph health to become "OK" times out during the ``platform-services``
  stage of ``sat bootsys boot``, the Ceph services will now be restarted on the
  storage nodes, and Ceph health will be waited on again.
- Fixed an error in the ``platform-services`` stage of ``sat bootsys boot``
  related to trying to start non-existent Ceph services.
- Fix a traceback that occurred if the user did not have permission to write to
  the log file.

### Added
- Added a check for running SDU sessions to the ``session-checks`` stage of a
  ``shutdown`` action in ``sat bootsys``.

### Security
- Incremented version of Alpine Linux from 3.13.2 to 3.13.5
  to address OpenSSL CVE-2021-3711.

## [3.9.0] - 2021-08-04

### Changed
- The ``--loglevel`` option is now an alias for the new ``--loglevel-stderr``.
- Remove the working directory ``/sat`` after the Docker container is built.
- Summaries generated by ``sat hwinv`` now have borders. Borders and headings may
  be toggled with ``--no-borders`` and ``--no-headings``.
- Changed the default logging level for stderr from "WARNING" to "INFO".
- Warn instead of rejecting on missing host keys in `sat bootsys` commands which
  use ssh to connect to other management NCNs.
- Disruptive shutdown stages in ``sat bootsys shutdown`` now prompt the user to
  continue before proceeding. A new option, ``--disruptive``, was added to
  bypass this when desired.
- Changed all informational print statements to be INFO level logging messages.

### Fixed
- Fixed a case where `sat xname2nid` and `sat nid2xname` failed when the input had
  extraneous whitespace.
- Fixed `--logfile` to accept a file name without leading directories.
- Fixed issues with filter error messages being printed twice or not being printed.
- Improved error messages when invalid filter syntax was supplied to
  refer to documentation of the syntax specification.
- Fixed an issue with specific field options not overriding `--fields` when listing
  components with `sat hwinv`.

### Added
- Added a ``--fields`` option to allow displaying only specific fields
  in subcommands which display a report.
- Added ``--loglevel-stderr`` and ``--loglevel-file`` to set logging level for
  stderr and log file separately.
- Added help and man page documentation on files that are absolute or relative
  paths in or below the home or current directory.
- Added prompt for whether user would like to continue when ``sat auth`` would
  overwrite an existing token.
- Added ``--excluded-ncns`` option to ``sat bootsys`` that can be used to omit
  NCNs from the platform-services and ncn-power stages in case they are
  inaccessible.
- Added support for ``--format json`` to print reports in JSON.
- Added support for the ``--filter``, ``--fields``, and ``--reverse`` options
  for summaries created by ``sat hwinv``.
- Added option to customize the default HTTP timeout length, both using the
  configuration file (with the ``api_gateway.api_timeout`` option) and with a new
  command line option, ``--api-timeout``.
- Added FRUID to output from ``sat hwinv``.
- Added a new ``sat hwhist`` subcommand to display hardware component history
  by xname (location) or by FRUID.

## [3.8.0] - 2021-06-23

### Changed
- When explicitly specifying a field using any ``--*-fields`` option with ``sat
  hwinv``, or when filtering against a field in any ``sat`` subcommand, those
  columns will now always be shown, even if all rows contain ``EMPTY`` or
  ``MISSING`` values.

### Fixed
- Fixed a case where filtering specific columns with any ``--*-fields`` option
  with ``sat hwinv`` failed when leading or trailing whitespace was present in
  the field name.
- Fixed the help text of `sat status` to list all available component types.
- Improved an error message which could sometimes occur when FAS reported a
  target with no xname.
- Fixed filtering so that the exact match of a column name used in the
  ``--filter`` query is always used instead of matching subsequences.
- Fixed filtering so that if there are multiple matches of column names
  using the ``--filter`` query, a WARNING is printed and the first match
  is used. This is consistent with ``--sort-by`` usage.
- Fixed filtering to handle spaces in column names by requiring them to
  be enclosed in double quotes.
- Changed warning message when filter returns no output to an error.

### Added
- Added power off of all non-management nodes in air-cooled cabinets
  to ``sat bootsys shutdown --stage cabinet-power``.
- Added a 'Subrole' column to the output of ``sat status``.
- Added ``sat bmccreds`` subcommand to provide a simple interface
  for setting BMC Redfish access credentials.
- Added ``sat slscheck`` subcommand to do a cross-check between SLS and HSM.
- Added confirmation message when ``sat setrev`` writes site info file to S3.

## [3.7.0] - 2021-05-13

### Changed
- Removed Redfish username and password from configuration file since
  they are no longer used by any subcommands.
- Changed the ``sat sensors`` command to use the Telemetry API to get
  sensor data instead of accessing Redfish directly.
- Changed the "unfreeze Ceph" step of the ``platform-services`` stage of
  ``sat bootsys boot`` to behave as follows:
  - Start any inactive Ceph services
  - Unfreeze Ceph
  - Wait for Ceph health
- Changed the ``platform-services`` stage of ``sat bootsys boot`` to prompt
  for confirmation of storage NCN hostnames in addition to Kubernetes managers
  and workers.

### Fixed
- Fixed a case where ``sat showrev`` fails when the Kubernetes configuration
  map ``cray-product-catalog`` is in an unexpected state.
- Improved error handling in ``sat showrev`` when connecting to the Kubernetes
  API fails.
- Added missing description of ``sat swap`` to output of ``sat --help``.
- Added back missing man pages to the container image.
- Removed an old ``slingshot-tools`` dependency from the RPM spec file.
  However, note that RPM installation has not been tested since the move to
  running ``sat`` in a container and is not officially supported.

### Added
- Added a new ``--update-until-timeout`` command-line option to ``sat sensors``.
- Added new fields to ``sat setrev`` and ``sat showrev``.
    - System description
    - Product number
    - Company name
    - Country code
- Added additional description of all fields when running ``sat setrev``,
  and added input validation for fields.
- Added a "Location Name" field to the listing of node accelerators output by
  `sat hwinv --list-node-accels`.

### Removed
- Removed the ``ceph-check`` stage of ``sat bootsys boot``.

## [3.6.0] - 2021-04-16

### Fixed
- Improved error handling in several cases of ``sat firmware``.
    - When multiple xnames and/or snapshots are given, a failure to query
      one of them will be logged as an error, but the valid snapshots
      and xnames will be printed.
    - If a given xname is not in a requested snapshot, a warning is logged.
    - If ``--snapshots`` is specified without arguments (to list all snapshot
      names) and xnames are provided on the command line, a warning is logged
      that the supplied xnames will be ignored.
    - If a given snapshot and/or xname combination yields no results,
      then the command will exit with an error.

### Changed
- Incremented version of Alpine Linux from 3.12.0 to 3.13.2.
- Changed the Ceph health check in ``sat bootsys boot --stage ceph-check``
  to be consistent with the check in the ``platform-services`` stage of
  ``sat bootsys boot`` and ``sat bootsys shutdown``.
- Changed the ``sat diag`` command to use the Fox API for launching controller
  diagnostics instead of accessing Redfish directly.

### Removed
- Removed Ansible and all of its dependencies from our container image by
  removing from our locked requirements files.
- Removed the ``cray-sat-crayctldeploy`` subpackage.
- Removed ``sat linkhealth`` which has been replaced by
  ``slingshot-topology-tool --cmd "show switch <ports,jacks> <switch xname>"``.
- Removed support for Firmware Update Service (FUS) in ``sat firmware``
  and ``sat bootsys shutdown --stage session-checks``. These commands now
  only use Firmware Action Service (FAS).

## [3.5.0] - 2021-03-24

### Added
- Added a new ``sat nid2xname`` subcommand to translate node IDs to node xnames.
- Added a new ``sat xname2nid`` subcommand to translate node and node BMC xnames
  to node IDs.

### Changed
- Changed ``sat swap`` to get all port policies when creating an offline port
  policy to check if the offline port policy already exists.
- Changed requirements files to ``requirements.txt`` and
  ``requirements-dev.txt``. Added ".lock" versions of these files and changed
  build process to use them, so that exact library versions are used.
- ``sat bootsys shutdown --stage bos-operations`` no longer forcefully powers
  off all compute nodes and application nodes using CAPMC when BOS sessions are
  complete or when it times out waiting for BOS sessions to complete.

### Fixed
- Addressed an error in ``sat bootsys``  when waiting for the ``hms-discovery``
  Kubernetes cronjob to be scheduled when there is no previous record of the
  job being scheduled.

## [3.4.0] - 2021-03-03

### Added
- Added a new ``--bos-templates`` command-line option and a ``bos_templates``
  configuration file option to ``sat bootsys boot|shutdown --stage bos-operations``.
  This is intended to replace ``--cle-bos-template``, ``--uan-bos-template``,
  and their respective configuration file options, ``cle_bos_template`` and
  ``uan_bos_template``.
- Added a confirmation message when generating a configuration file via
  ``sat init``.

### Changed
- ``--cle-bos-template`` and ``--uan-bos-template`` now no longer have defaults
  for ``sat bootsys boot|shutdown --stage bos-operations``. If a CLE or UAN
  session template is not specified then it will not be used for the boot or
  shutdown.
- Changed the default for s3.endpoint in ``sat.toml``
  from ``https://rgw-vip`` to ``https://rgw-vip.nmn``.
- Changed ``sat firmware`` to display both 'name' and 'targetName' fields from
  FAS, and changed the 'ID' header in the table to read 'name'.
- Improved step of ``sat bootsys shutdown --stage platform-services`` that stops
  containers by adding prompt whether to continue if stopping containers fails
  and added log messages about running and stopped containers.
- Improved console logging during `sat bootsys boot|shutdown --stage ncn-power`
  by adding a check for active screen sessions after they are created to account
  for the case when some other process like conman is holding the console.
- Changed info-level log messages to print statements for important messages
  about progress during the `ncn-power` stage of `sat bootsys`.

### Fixed
- Changed "BIS server" in SAT man page to "Kubernetes manager nodes", reworded
  description to discuss all of SAT's uses, and corrected several small typos
  in the SAT man page.
- Improved error handling in ``sat showrev`` when the cray-product-catalog
  Kubernetes configuration map does not exist, and when an invalid value is
  given for the S3 endpoint URL.
- Stopped printing a byte string of every container ID that was stopped during
  ``sat bootsys shutdown --stage platform-services`` when ``crictl stop``
  command times out.

## [3.3.0] - 2021-02-05

### Changed
- Changed method of getting hostnames of management non-compute nodes (NCNs) in
  ``sat bootsys`` from using Ansible groups to using the ``/etc/hosts`` file.
- Changed the platform services stage of ``sat bootsys shutdown`` to
  shut down containerd containers using crictl, and to stop the containerd
  service using ``systemctl``.
- Changed the platform services stage of ``sat bootsys shutdown`` to check
  health of the Ceph cluster and freeze the Ceph cluster before shutting down.
- Changed the platform services stage of ``sat bootsys boot`` to check
  health of the Ceph cluster and unfreeze the Ceph cluster before booting.
- Changed the platform services stage of ``sat bootsys boot`` to start
  containerd on the management NCNs and ensure it's enabled.
- Changed the platform services stage of ``sat bootsys shutdown`` to stop and
  disable kubelet on the Kubernetes management NCNs.
- Changed the platform services stage of ``sat bootsys boot`` to start and
  enable kubelet on the Kubernetes management NCNs.
- Changed the platform services stage of ``sat bootsys shutdown`` to save a
  snapshot of etcd and stop the etcd service on the manager Kubernetes NCNs.
- Changed the platform services stage of ``sat bootsys boot`` to ensure etcd is
  started and enabled on the manager Kubernetes NCNs.
- Changed ``sat swap switch`` to use the new Fabric Manager API.
- Changed the ``ncn-power`` stage of ``sat bootsys`` to no longer start and stop
  dhcpd, which is unnecessary now that NCNs and their management interfaces have
  statically assigned IP addresses.
- Changed the command prompt in ``sat bash`` to display 'sat-container' in
  addition to the container ID.
- Changed the ``ncn-power`` stage of ``sat bootsys`` to start console monitoring
  of NCNs using ``screen`` sessions launched over an SSH connection to ncn-m001
  instead of using ``ipmi_console_start.sh`` and ``ipmi_console_stop.sh``
  scripts.
- Changed the ``ncn-power`` stage of ``sat bootsys`` to exit with an error if it
  cannot start console monitoring prior to booting or shutting down NCNs.
- Changed ``sat linkhealth`` to correctly process status output from
  the Redfish API for newer versions of Rosetta switch firmware.
- Changed ``sat swap cable`` to use the new Fabric Manager API and Shasta p2p file.

### Removed
- Removed the ``hsn-bringup`` stage of ``sat bootsys boot`` due to removal of
  underlying Ansible playbook, ``ncmp_hsn_bringup.yaml``, and old fabric
  controller service.
- Removed call to ``ncmp_hsn_bringup.yaml`` Ansible playbook from currently
  unused ``HSNBringupWaiter`` class.
- Removed calls to removed Ansible playbooks ``enable-dns-conflict-hosts.yml``
  and ``disable-dns-conflict-hosts.yml`` during ``ncn-power`` stage of
  ``sat bootsys``.
- Removed the ``bgp-check`` stage of ``sat bootsys {boot,shutdown}`` due to
  removal of underlying Ansible playbook that implemented this stage.
- Removed ``run_ansible_playbook`` function from ``sat.cli.bootsys.util`` module
  since it is no longer used anywhere.
- Removed ``RunningService`` context manager since it is no longer used.

### Fixed
- Removed error message and 'ERROR' value for Slurm version in system
  table in ``sat showrev`` when Slurm is not present.
- Add missing space in help text for ``sat showrev`` ``--all`` option.

### Security
- Incremented required version of Python PyYAML package to 5.4.1.
- Incremented required version of Python RSA package to 4.7.

## [3.2.0] - 2020-12-17

### Changed
- Changed ``sat showrev`` to display product information from kuberetes
  configuration map. Previous product information is now accessible with
  the ``--release-files`` option.
- Changed ``sat showrev`` to display separate tables for system-wide
  information and host-local information. Added the ``--local`` option to
  ``sat showrev``.
- ``sat showrev`` will first read from ``/opt/cray/sat/etc/os-release``
  and from ``/etc/os-release`` if that does not exist for the SLES
  version.
- Modified output and logging of ``sat bootsys boot|shutdown --stage bos-operations``
  to include more information about the BOS session, BOA jobs and BOA pods.
- Changed ``sat swap`` to print an error message since the Fabric Controller API
  that is used is no longer available.

### Removed
- Removed Lustre and PBS versions from ``sat showrev``.
- Removed ``--packages`` and ``--docker`` options from ``sat showrev``.
- Removed package and docker image listing from output of
  ``sat showrev --all``.
- Removed ``sat cablecheck``.
- Removed ``slingshot-tools`` from the Docker image.

### Fixed
- Improved error handling in ``sat showrev --docker``.
- Fixed a missing comma in the ``sat`` man page.
- Added a space between sentences in S3 error logging in ``sat showrev``.

## [3.1.0] - 2020-12-04

### Added
- Ability to list node enclosure power supplies in ``sat hwinv`` with
  ``--list-node-enclosure-power-supplies``.
- Ability to list node accelerators (e.g. GPUs) in ``sat hwinv`` with
  ``--list-node-accels``.
- New field for accelerator counts when listing and summarizing nodes
  in ``sat hwinv``.
- Ability to list node accelerator risers (e.g. Redstone Modules)
  in ``sat hwinv`` with ``--list-node-accel-risers``.
- New field for accelerator riser counts when listing and summarizing nodes
  in ``sat hwinv``.
- Ability to list node HSN NICs in ``sat hwinv`` with ``--list-node-hsn-nics``.
- New field for HSN NIC counts when listing and summarizing nodes
  in ``sat hwinv``.

### Changed
- Changed ``sat bootsys`` state capture and hsn/k8s checks to use an S3
  bucket instead of local files.
- ``sat setrev`` now writes the site information file to S3, and
  ``sat showrev`` now downloads the site information file from S3.
- Changed default logging directory to ``/var/log/cray/sat/sat.log``.

### Removed
- Removed parsing of ``/etc/cray-release`` from ``sat showrev``.

### Fixed
- Fixed dumping of serial number in ``sat setrev`` so that it is always
  a string.

## [3.0.0] - 2020-11-18

### Added
- New ``sat init`` subcommand that generates a config file for the user at
  ``$HOME/.config/sat/sat.toml`` and populates it with defaults.
- ``Dockerfile`` to build a Docker image containing sat and its
  dependencies, including ipmitool, kubectl, and slingshot-tools.
- ``requirements.docker.txt`` that explicitly specifies the ``sat`` python
  package's dependencies and their versions that are installed in the Docker
  image.
- ``Jenkinsfile.docker`` that builds the Docker image in a DST pipeline.

### Changed
- Changed default location of configuration file from ``/etc/sat.toml`` to
  ``$HOME/.config/sat/sat.toml`` to more easily allow each user to have their
  own configuration file.
- Modified all ``sat`` commands to generate a config file at the new default
  location, ``$HOME/.config/sat/sat.toml``, if one does not exist yet.
- Renamed ``Jenkinsfile`` to ``Jenkinsfile.rpm`` to differentiate from the newly
  added ``Jenkinsfile.docker`` that builds the Docker image.
- Moved sat from the shasta-standard and shasta-premium product streams to the
  sat product stream.

### Fixed
- Updated Vendor tag in RPM spec file to HPE.
- Fixed RPM build failure in DST pipeline by removing `BuildRequires` tags that
  result in conflicting requirements installed in container used to build RPM.

### Security
- Incremented required version of python cryptography package from 3.1 to 3.2.

## [2.4.0] - 2020-10-08

### Added
- ``sat bootsys shutdown`` and ``sat bootsys boot`` have been split into stages
  which are specified with ``--stage``. Behavior of ``sat bootsys shutdown``
  without stage specified is to run the ``session-checks`` stage for backwards
  compatibility with the previous release.
- Stages added to ``sat bootsys shutdown`` to automate additional stages of the
  system shutdown procedure. Stages are as follows:
    - capture-state: captures state of HSN and k8s pods on the system.
    - session-checks: checks for active sessions in BOS, CFS, CRUS, FAS, and NMD
      services.
    - bos-operations: shuts down compute nodes and User Access Nodes (UANs)
      using BOS.
    - cabinet-power: shuts down power to the liquid-cooled compute cabinets in
      the system and suspends hms-discovery cronjob in k8s.
    - bgp-check: checks BGP peering sessions on spine switches and
      re-establishes if necessary.
    - platform-services: stops platform services running on management NCNs.
    - ncn-power: shuts down and powers off the management NCNs.
- Stages added to ``sat bootsys boot`` to automate additional stages of the
  system boot procedure. Stages are as follows:
    - ncn-power: powers on and boots managment NCNs.
    - platform-services: starts platform services on management NCNs.
    - k8s-check: waits for k8s pod health to reach state from before shutdown.
    - ceph-check: restarts ceph services and waits for them to be healthy.
    - bgp-check: checks BGP peering sessions on spine switches and
      re-establishes if necessary.
    - cabinet-power: resumes hms-discovery cronjob in k8s, waits for it to be
      scheduled, and then waits for chassis in liquid-cooled cabinets to be
      powered on.
    - hsn-bringup: brings up the HSN and waits for it be as healthy as it was
      before shutdown.
    - bos-operations: boots compute nodes and User Access Nodes (UANs) using
      BOS.
- Debug logging for every stage of `sat bootsys` operations including duration
  of each stage.
- Developer documentation in markdown format.
- Added ``sat swap`` subcommand for swapping cables and switches.  The
  existing functionality of ``sat switch`` is now duplicated under
  ``sat swap switch``, and ``sat switch`` is deprecated.  Changed
  exit codes of ``sat switch`` to align with ``sat swap``.

### Fixed
- Fixed missing values in info messages logged from sat.filtering module.
- Stopped using deprecated "cray" public client and started using new "shasta"
  public client for authentication.
- Respect configured stderr log level and stop emitting duplicate log messages
  to stderr.
- Fixed typos on ``sat linkhealth`` and ``sat status`` man pages.
- Added ``show_empty`` and ``show_missing`` FORMAT config file options to
  ``sat`` man page.
- Added sat-switch subcommand to ``sat`` man page.
- ``sat firmware`` now logs an error for unknown xnames.
- Fixed bug in flattening of list of NCN hostnames in the ``ncn-power`` stage of
  ``sat bootsys boot``.

## [2.3.0] - 2020-07-01

### Added
- Kubernetes pod state is dumped to a file during ``sat bootsys shutdown``.

### Fixed
- Fixed incorrect FAS URL used by ``sat firmware`` commands.
- Fixed minor bug in FAS error handling in ``sat firmware``.
- Stopped logging tokens when log level is set to debug.

## [2.2.0] - 2020-06-11

### Added
- FAS support for ``sat firmware``.
- Added ``sat bootsys`` subcommand and implemented first portion of the
  ``shutdown`` action.

### Changed
- Author in man pages now reads HPE.
- Split contributing guidelines to separate ``CONTRIBUTING.md`` file and added
  instructions for signing off on the Developer Certificate of Origin (DCO).

### Removed
- Removed Kibana objects, supporting scripts, and metadata from RPM. The
  ``sat`` command is not affected.

### Fixed
- Fixed two critical errors in ``sat showrev --system`` that resulted in an
  uncaught ``TypeError`` or ``IndexError``.
- ``sat k8s`` and ``sat showrev`` now catch ``FileNotFoundError`` that can be
  raised when loading kubernetes config.
- Suppressed ugly ``YAMLLoadWarning` that appeared when loading kubernetes
  config in ``sat k8s`` and ``sat showrev`` commands.

## [2.1.1] - 2020-06-03

### Changed
- ``sat hwmatch`` now displays a message if no mismatches were found.
- ``sat cablecheck`` now calls ``/usr/bin/check-hsn-cables`` which is the new
  name of the script after a slingshot-tools packaging refactor.

## [2.1.0] - 2020-05-26

### Added
- Extended Kibana dashboard for rasdaemon with panels that show just errors.
- Kibana dashboard to show heartbeat losses.
- New column showing ratio of co-located replicas to running pods for a given
  replicaset in output of ``sat k8s``.
- Support for exact field name matching using double quotes in ``sat hwinv``.

### Changed
- ``sat cablecheck`` now directly executes ``check_hsn_cables.py`` instead of
  calling with ``python2``.
- Changed "MISSING" values to "NOT APPLICABLE" when cable is not present in
  ``sat linkhealth``.

### Removed
- Removed "flow_control_config" field from ``sat linkhealth``. It is no longer
  present in Redfish, by design.

### Fixed
- Man page for ``sat diag`` updated to state explicitly what devices it can
  be applied to.
- Man page for ``sat showrev`` updated to describe the release directory and
  provide an example of products output.
- Restored certificate-nonvalidation warning circumvention from ``sat diag``,
  ``sat linkhealth``, and ``sat sensors``.

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
