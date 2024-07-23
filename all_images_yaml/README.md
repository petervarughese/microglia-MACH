# Yaml files 
These files contain image-specific information for executing the mach code
At a minimum, these should contain the filename and coordinates containing a region of interest. 
In this minimal case, all other necessary parameters are obtained from Params.yaml in the parent directory. 

In the event that the Params.yaml default parameter values are nonoptimal, updated parameters like rodSNR can be defined. These will supercede the values initially set by Params.yaml 

## Index
- google spreadsheet available at https://docs.google.com/spreadsheets/d/1S6Fp3re726sTNgJGzDRFrNZ2M8vzNKbUENbxKszRRtQ/edit?gid=0#gid=0
- annotate these as files are examined 

## Validation 
- At this time, the mach filtering results have not been inspected for the individual images. 
To signify this status, each yaml has a flag to indicate that the yaml has been validated 
```
validated: False 
```

After the results have been inspected and parameters optimized, the validated tag can be updated, e.g. 
```
validated: True # or pkh/pv 
```

