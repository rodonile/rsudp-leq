# Description:

This folder contains configuration files examples for this rsudp fork. Move the configuration file (rsudp_settings.json) into the .config/rsudp folder in your home directory.

# Explanations:

## "settings":
- "station": OFFLN  --> trigger use of offline inventory file (in inventory_files folder) for deconvolution (does not attempt to download it from the server)

## "plot":
- "decibel": true --> adds live intensity (dB) plot
- "leq": true --> adds live Leq () plot, i.e. equivalent continuous sound energy

## "alert_leq":
- "sta": short term interval for Leq calculation
- "lta": long term interval for Leq calculation
