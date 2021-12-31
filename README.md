

# Examples

Add to configuration.yaml, to load the customization:
```yaml
zha_custom:
```

Add to logger configuration:
```yaml
logger:
  log:
    zha_custom: debug
```

https://homeassistant.local:8123/developer-tools/service
Choose `zha_custom.execute`


Examples are work in progress, may not be functionnal


```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:22:08:ed:1a
  command: scan_device
```


```yaml
service: zha_custom.execute
data:
  ieee: 00:15:8d:00:04:7b:83:69
  command: bind_ieee
  command_data: 00:12:4b:00:22:08:ed:1a

```

```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:22:08:ed:1a
  command: handle_join
  command_data: 0x604e

```


```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: attr_write
  # Data: Endpoint, Cluster ID, Attribute Id, Attribute Type, Attribute Value
  command_data: 11,0x0006,0x0000,0x10,1
```


Configure Temperature reporting on a SonOff SNZB-02 (eWeLink/TH01).
Note that you (may) need to press the button on the thermometer just after
requesting the command.
I got timeouts for these commands, but at least one of them passed and
the temperature reporting was in practice every 20s (probably the minimum
of the device itself) for changes of minimum 0.10 degC.

```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:23:b3:da:a5
  command: conf_report
  command_data: 1,0x0402,0x0000,5,300,10
```


# Backup ZNP network data (to transfer later, backup or simply get network key)

```yaml
service: zha_custom.execute
data:
  command: znp_backup
```
