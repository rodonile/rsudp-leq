# The Windows branch
This is a minimal version of rsudp with only the relevant modules and dependencies for the use case of small ground vibration disturbance detection, ready for production deployment in windows OS.

## Table of Contents  
- [Installation instructions](#installation-instructions)  
- [How to start the program](#how-to-start-the-program)
- [Configuration File Parameters](#configuration-file-parameters)
- [Database storage and visualization](#database-storage-and-visualization)

![GUI](docs/rsudp_gui_rodonile.png)

## Installation instructions
- Clone this repo
- Run the [installation script](win-install-rsudp.bat) by double-clicking it.

## How to start the program
- Run the [start script](win-start-rsudp.bat) by double-clicking it.
- Suggestion: create a shortcut to this file that can be run from everywhere (e.g. the Desktop)

# Configuration File Parameters
A configuration file is automatically placed in the **C:\users\\%USERNAME%\\.config\rsudp** folder by the install script. An [example config file](config_file_sample.json) is also available in this repo. You will probably need to change the location of the inventory file and desired output directory.

## settings:
- **port**: UDP port where the program listens for packets. The port is specified on the raspberry shake Admin Webpage toghether with the destination IP Address:  
        <img src="docs/rs_webgui_datacast.PNG" width="350" height="225">
  
- **station**: OFFLN  --> use offline inventory file (in inventory_files folder).
- **scaling_sensitivity**: sensitivity of the geophone. This parameter is used to compute velocity [$m/s$] from the AD-converter voltage counts. It is only used in modules where the *scaling* option is set to true. Default value: 250000000 [$counts/(m/s)$].
- **db_reference**: reference velocity value to compute dB intensity. Default value: 1 $\mu m/s$ (1e-6).
- **debug**: if true send text to command line. Default: true (recommended).

## plot:
This is the standard live plotting module from rsudp extended to enable displaying of intensity(dB) as well as Leq(dB) values.

- **duration**: Inverval in seconds for the live plot. Default 60s.
- **spectrogram**: show spectrogram of the signal. Default: true.
- **decibel**: adds live intensity (dB) plot with Leq average. Default: true.
- **voltage**: shows live voltage estimation. Default: false.
- **fullscreen**: fullscreen window mode. Default: true
- **kiosk**: fullscreen + force the plot to fill the entire screen (used for showing continuously in monitoring display). Default: false.
- **event_screenshot**: produce a screenshot of the waveforms/spectrogram when an alert is triggered (e.g. by the alert_leq_IIR module)
- **scaling**: compute velocity using the *scaling_sensitivity* parameter. If disabled the plot shows voltage counts from the AD converter.

## alert_leq_IIR:
This module uses an IIR filter to compute the STA and LTA Leq, hence it doesn't require storing all the samples in the buffer. This allows to have longer LTA intervals while running without issue on light hardware (e.g. Raspberry Pi). Also it doesn't require a "warmup" time before the trigger is activated. The module also supports a static value for the LTA Leq.

IIR first order filter:

    y[n+1] = a * y[n] + (1-a) * x[n+1]
    
    a <-- "remembering" factor (lower = filter forgets old values easily)
    a ~ 10 ^ ( filter_loss[dB] / (20 * T * fs) )

- **a_sta**: "remembering" factor for the IIR filter for the STA calculation
- **a_lta**: "remembering" factor for the IIR filter for the LTA calculation
- **static_lta**: use a static value for the LTA instead of an Leq calculation (preferred method, as varying LTA would contains also high noise events in the calculation)
- **lta**: Value for LTA if *static_lta* is set to true. Default 10dB (computed with 1 $\mu m/s$ (1e-6) dB reference).
- **scaling**: compute velocity using the *scaling_sensitivity* parameter. If disabled the calculations are performed using voltage counts from the AD converter.

## write:
This module to push data to the database and/or write data to disk.....finish here

## forward:

## printdata:
This module is used to print data directly to the command line as it arrives from the Raspberry shake (used only for debugging purposes).


# Database storage and visualization
Refer to the README in the **visualization** folder for instruction on how to setup the database+visualization stack, add new influxdb buckets, grafana dashboards, etc..

TODO: add grafana screenshot, link to visualization folder for more documentation on how to set it up & create new buckets etc...

