"""
Entry point for the sensors subcommand.

Copyright 2020 Cray Inc. All Rights Reserved.
"""

import logging
import sys

from sat.config import get_config_value
import sat.redfish

from sat.cli.sensors.sensortypes import (
    SensorsParser, VoltageMarginsParser, TemperaturesParser,
    VoltagesParser, FansParser, PowerSuppliesParser)

from sat.cli.sensors.bmc import BMCType, RiverType, SwitchType, ResponseStatus
from sat.cli.sensors.capture import CaptureManager

LOGGER = logging.getLogger(__name__)


def do_sensors(args):
    """Queries sensor readings from BMCs specified on the command line.

    The BMCs may be listed by xname, hostname alias, or IP address. The type
    of each BMC is determined without additional input from the user. For some
    types, the xname sufficies, but it is not suffcient to rely only on xname
    in these cases, since the provided identifier may be something else. A
    heuristic approach is used when the identifier is not sufficient.

    The type of BMC determines which sensor parsers are invoked upon it, and
    these parsers gather the sensor data.

    The readings that result are displayed in a tabular format using the standard
    Report class.

    Arguments:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    if not args.xnames:
        LOGGER.error("No xnames were supplied.")
        sys.exit(1)

    username, password = sat.redfish.get_username_and_pass(args.redfish_username)

    # If there's no capture, manager is a pass-through
    capture_mgr = CaptureManager(args)

    sensors_parser = SensorsParser()
    voltage_margins_parser = VoltageMarginsParser()
    voltages_parser = VoltagesParser()
    power_supplies_parser = PowerSuppliesParser()
    temperatures_parser = TemperaturesParser()
    fans_parser = FansParser()

    report = capture_mgr.get_report([
        'bmc', 'sensor number', 'electrical context', 'device context', 'physical context',
        'physical subcontext', 'index', 'sensor type', 'reading', 'units'],
        None, args.sort_by, args.reverse,
        get_config_value('format.no_headings'),
        get_config_value('format.no_borders'),
        filter_strs=args.filter_strs)

    n = 0

    for xname in args.xnames:
        bmc = capture_mgr.bmc_factory(xname, username, password)
        bmc.detect_type()

        if not bmc:
            # Initialization failed. unable to detect type, or possibly a bad request.
            # The cause should be well-logged; move on to the next xname.
            continue

        if bmc.type is BMCType.CHASSIS:
            # Entries are present, but almost never any readings when inspected
            # temperatures_parser(bmc)
            # voltages_parser(bmc)

            sensors_parser(bmc)

        if bmc.type is BMCType.SWITCH:
            wrapped_rsp = temperatures_parser(bmc)

            if wrapped_rsp.status is not ResponseStatus.CONNECTION_ERR:
                voltages_parser(bmc)
                if bmc.sub_type is SwitchType.MARGINS:
                    voltage_margins_parser(bmc)

        # Mountain nodes
        if bmc.type is BMCType.NODE:
            wrapped_rsp = temperatures_parser(bmc)

            if wrapped_rsp.status is not ResponseStatus.CONNECTION_ERR:
                voltages_parser(bmc)
                sensors_parser(bmc)

        # River nodes
        if bmc.type is BMCType.RIVER:
            if bmc.sub_type is not RiverType.UNKNOWN:
                wrapped_rsp = temperatures_parser(bmc)

                if wrapped_rsp.status is not ResponseStatus.CONNECTION_ERR:
                    power_supplies_parser(bmc)
                    voltages_parser(bmc)
                    fans_parser(bmc)

        LOGGER.info('%s sensors were queried from %s.', len(bmc.sensors), xname)

        if len(bmc.sensors) == 0:
            LOGGER.warning('%s responded with no sensors!', xname)

        for sensor in bmc.sensors:
            ctxt = sensor.context
            msmt = sensor.measurement

            report.add_row([xname, ctxt.sensornum, ctxt.electrical, ctxt.device, ctxt.physical,
                            ctxt.physicalsub, ctxt.index, msmt.type, msmt.reading, msmt.units])

        n += 1

    LOGGER.info('%s sensors were queried from %s BMCs.', len(report.data), n)

    capture_mgr.shutdown()

    if args.format == 'yaml':
        print(report.get_yaml())
    else:
        print(report)