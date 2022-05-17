# Description:

This folder contains configuration files examples for this rsudp fork. The rsudp install script should have copied this script to the *.config/rsudp* folder in the HOME directory.

# Explanations:

## "settings":
- "station": OFFLN  --> trigger use of offline inventory file (in inventory_files folder) for deconvolution (does not attempt to download it from the server)

## "plot":
This is the standard plotting module from rsudp extended to enable displaying of intensity(dB) as well as Leq(dB) values.

- "decibel": true --> adds live intensity (dB) plot
- "leq": true --> adds live Leq () plot, i.e. equivalent continuous sound energy
- "db_offset": linear offset on dB values (calibration) - NOT YET IMPLEMENTED

## "alert_leq":
This module uses the same approach as the "alert" module in rsudp: all the samples for the relevant interval (current_time - lta_interval, current_time) are stored in an array. The array is used to compute Leq values and updated.

- "sta": short term interval for Leq calculation
- "lta": long term interval for Leq calculation
- "db_offset": linear offset on dB values (calibration) - NOT YET IMPLEMENTED

## "alert_leq_IIR":
This module uses an IIR filter to compute the STA and LTA Leq, hence it doesn't require storing all the samples in the buffer. This allows to have longer LTA intervals while running without issue on light hardware (e.g. Raspberry Pi). 
IIR first order filter:

    y[n+1] = a * y[n] + (1-a) * x[n+1], where a ~ 10 ^ ( filter_loss[dB] / (20 * T * fs) )  ("remembering" factor)

- "db_offset": linear offset on dB values (calibration) - NOT YET IMPLEMENTED
- "a_sta": "remembering" factor for the IIR filter for the STA calculation
- "a_lta": "remembering" factor for the IIR filter for the LTA calculation
