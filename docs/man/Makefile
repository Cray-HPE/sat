all: \
	sat-auth.8 \
	sat-bootsys.8 \
	sat-cablecheck.8 \
	sat-diag.8 \
	sat-firmware.8 \
	sat-hwinv.8 \
	sat-hwmatch.8 \
	sat-k8s.8 \
	sat-linkhealth.8 \
	sat-sensors.8 \
	sat-setrev.8 \
	sat-showrev.8 \
	sat-status.8 \
	sat-swap.8 \
	sat-switch.8 \
	sat.8

%.8: %.8.rst
	rst2man.py $< $@

clean:
	rm -f *.8

.PHONY: all clean
