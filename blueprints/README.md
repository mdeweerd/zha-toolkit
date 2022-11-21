- `backup.yaml`:\
  Script for daily backup of supported zigbee coordinators.
- `backup_znp.yaml`:\
  Script for daily backup of ZNP coordinator.
- `blueprint_danfoss_ally_configure_script.yaml`:\
  Sample blueprint script
  to configure Danfoss Ally (see other script example for a more complete
  configuration)
- `danfoss_ally_remote_temperature.yaml`:\
  Send temperature to Danfoss Ally
  TRV at most every X minutes and at least every Y minutes. Uses restart to
  interrupt long wait ("y minutes")
- `danfoss_ally_remote_temperature_min_delay.yaml`:\
  Send temperature to
  Danfoss Ally at most every X minutes. Uses single to block too fast
  updates. In case the temperature is stable over a very long time, you
  should ensure that HA considers it is updated on every change.
- `danfoss_ally_remote_temperature_min_delay_fake_change.yaml`:\
  Same as
  `..._min_delay.yaml`. Work in progress - needs update of
  `home-assistant-variables`. Uses
  [snarky-snark/home-assistant-variables](https://github.com/snarky-snark/home-assistant-variables)
  to fake temperature update even when stable by applying slight change in
  temperature at the end of the minimum delay. So if the temperature is
  stable, it will still be seen as a change.
- `script_Thermometer_setReporting.yaml`:\
  Blueprint Script to configure
  reporting of a zigbee device with Temperature Measurement Cluster 0x0402.
