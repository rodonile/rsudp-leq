# Description:

This folder contains configuration files examples for this rsudp fork. The rsudp install script should have copied the configuration file to the *.config/rsudp* folder in the HOME directory.

# Explanations:

## settings:
- **station**: OFFLN  --> trigger use of offline inventory file (in inventory_files folder) for deconvolution (does not attempt to download it from the server)
- **scaling_sensitivity**: sensitivity of the geophone. This parameter is used to compute velocity [$m/s$] from the AD-converter voltage counts. It is only used in modules where the *manual_scaling* option is set to true. Default value: 250000000 [$counts/(m/s)$]. It provides and alternative to the built-in obspy deconvolution module. 
- **db_reference**: reference velocity value to compute dB intensity. Default value: 1 $\mu m/s$ (1e-6).

## plot:
This is the standard plotting module from rsudp extended to enable displaying of intensity(dB) as well as Leq(dB) values.

- **decibel**: true --> adds live intensity (dB) plot with Leq average
- **voltage**: true --> shows live voltage counts
- **manual_scaling**: true --> directly compute velocity using the *scaling_sensitivity* parameter instead of the deconvolution module. If this is set to true, the *deconvolve* option is overwritten (no matter if true or false).

## alert_leq_IIR:
This module uses an IIR filter to compute the STA and LTA Leq, hence it doesn't require storing all the samples in the buffer. This allows to have longer LTA intervals while running without issue on light hardware (e.g. Raspberry Pi). 
IIR first order filter:

    y[n+1] = a * y[n] + (1-a) * x[n+1], where a ~ 10 ^ ( filter_loss[dB] / (20 * T * fs) )  ("remembering" factor)

- **a_sta**: "remembering" factor for the IIR filter for the STA calculation
- **a_lta**: "remembering" factor for the IIR filter for the LTA calculation
- **static_lta**: true --> use a static value for the LTA instead of an Leq calculation
- **lta**: Value for LTA if *static_lta* is set to true. Default 10dB (computed with 1 $\mu m/s$ (1e-6) dB reference).
- **manual_scaling**: true --> directly compute velocity using the *scaling_sensitivity* parameter instead of the deconvolution module. If this is set to true, the *deconvolve* option is overwritten (no matter if true or false).

## alert_leq (older, first idea):
This module uses the same approach as the "alert" module in rsudp: all the samples for the relevant interval (current_time - lta_interval, current_time) are stored in an array. The array is used to compute Leq values and updated.

- **sta**: short term interval for Leq calculation
- **lta**: long term interval for Leq calculation