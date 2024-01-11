# Ceng Raytracer Exporter for Blender
## Installation
Install the ceng_exporter.py file as an addon in Blender.
Blender 3.6+ is supported.
## Usage
File -> Export -> CengRaytracer
## Supported Content
- Background Color: Blender Scene World Background Color
- Shadow Ray Epsilon: constant = 1e-3
- Max Recursion Depth: constant = 6
- Cameras: Multiple cameras supported, ImageName = Camera name (.jpg is added automatically)
- Lights: Only point lights supported
- Materials: Only Principled BSDF setup is supported
    - Ambient Reflectance: always zero
    - Diffuse Reflectance: color input from BSDF node
    - Specular Reflectance: specular input from BSDF node
    - Mirror Reflectance: 1 - roughness input from BSDF node (1 roughness = 0 mirror and vice versa)
    - PhongExponent: always one
- Textures: Texture input in BSDF node's diffuse socket is accepted
    - Decal mode always kd
- Objects: Multiple objects supported
- UVs: Single channel UVs supported

## Contribution Options
- The script is open to extension/modification. For example options like max recursion depth can be exposed in the export panel.
- Transformations not supported but should be trivial to implement. 
