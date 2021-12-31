

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
