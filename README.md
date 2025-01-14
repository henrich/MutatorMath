[![Build Status](https://travis-ci.org/LettError/MutatorMath.svg?branch=master)](https://travis-ci.org/LettError/MutatorMath)
[![Coverage Status](https://coveralls.io/repos/LettError/MutatorMath/badge.svg?branch=master&service=github)](https://coveralls.io/github/LettError/MutatorMath?branch=master)

MutatorMath
===========

![A MutatorMath Colorfield](mutatorMath_colorField.jpg)

MutatorMath is a Python library for the calculation of piecewise linear interpolations in n-dimensions with any number of masters. It was developed for interpolating data related to fonts, but if can handle any arithmetic object.


* The **objects/** subpackage contains the general calculation tools.
* The **ufo/** subpackage contains tools to specifically process UFO data. 
* MutatorMath has no user interface, just the math.

## License

The MutatorMath package is published under the [BSD-3 license](http://opensource.org/licenses/BSD-3-Clause).

## Dependencies

The basic Mutator and Location objects will run on any standard Python 2.7 or higher distribution, but has not been tested on Python 3.x.

The UFO processing tools in MutatorMath need some additional libraries. Note that anticipating the move to UFO3, MutatorMath already uses the UFO3 branches for Defcon, FontMath and UFOLib. While these modules have received a lot of testing, these are not the main branches yet.

| Library  | Author             | Branch | URL                                              |
| -------- | ------------------ | ------ | ------------------------------------------------ | 
| Defcon   | TypeSupply.com     | ufo3   |  https://github.com/typesupply/defcon            |
| FontMath | TypeSupply.com     | ufo3   |  https://github.com/typesupply/fontMath          |
| Robofab  | RoboFab Consortium | ufo3k  |  https://github.com/robofab-developers/robofab   |

## MutatorMath terminology

*   **designspace**:    abstract Euclidian space with any number of dimensions.
*   **axis**:           A dimension in the designspace. Dimension names can be descriptive, for instance `x`, `y`, `width`, `weight`, `pop`, `snap`.
*   **location**:       Coordinates of a point in the designspace stored as a dictionary of named dimensions. For instance `Location(x=0)` and `Location(x=10)` are in the same dimension, whereas `Location(snap=10)` is not. There will be implementation limits on the number of dimensions, but theoretically there is no limit.
*   **split location** or **ambivalent location**: A location in which one or more dimensions have a 2-tuple rather than a single value. This is used to describe anisotropic locations. For instance `Location(weight=(50, 60))` means the horizontal value is 50, the vertical value is 60. Support for anisotropic coordinates is only 2 dimensional. 
*   **origin**:         A special location at which all dimension values are 0. Unnamed dimensions are assumed to be zero. `Location()` is at the _origin_. 
*   **on-axis**:        A location with a single non-zero axis value. `Location(width=1000)` is considered to be on-axis.
*   **off-axis**:       A location with more than one non-zero axis value. `Location(width=1000, weight=1000)` is considered to be off-axis.
*   **bias**:           A design space vector that translates all masters and instances.
*   arithmetic support
    *   objects that offer arithmetic behavior
    *   objects that respond to `+`, `-`, `*` and `/`
    *   objects with `__add__`, `__sub__`, `__mul__`, `__rmul__`, `__div__` and `__rdiv__` methods
*   **master**:         an arithmetic object that provides the input data.
*   **neutral**:        a master inserted at the origin
*   **instance**:       an object calculated at a specific location, same class as the master.

## Building a Mutator

A convenient Mutator builder function `buildMutator()` accepts a list of `(location, object)` pairs. Internally it sorts the neutral / on / off axis masters and calculates the bias.

* Master locations must not overlap.
* For a more in-depth examples of building Mutator objects, read the doctests.

UFO
===

A UFO stores data related to the design and production of fonts (specification at [UnifiedFontObject.org](http://unifiedfontobject.org). The ufo/ subpackage contains some tools to make the building and processing of UFO mutators easier.

## Designspace document

The requirements for a UFO designspace will differ from project to project. The location of the masters and instances, special wishes for kerning and specific glyphs etc. This package provides tools to read and write a description of a designspace to XML. Such a file stores all information necessary: which source UFOs, where to insert them, which glyphs to generate, which instances etc.

* A designspace document can be processed by a simple python build script. (See `buildExample.py`). That makes it possible to build instances on remote computers, as part of cron jobs etc.
* Examples and tests of the reader and writer can be found in the `test/ufo/` directory.
* MutatorMath proposes the `.designspace` extension.

## Designspace XML structure


A `.designspace` file contains all data needed for setting up interpolations between a number of master UFOs. A more comprehensive specification of the .designspace structure will follow. 

```xml
<?xml version="1.0" ?>
<designspace format="3">
    <sources>
        <source filename="../sources/Light/font.ufo" name="master_1">
            <lib copy="1"/>
            <groups copy="1"/>
            <info copy="1"/>
            <location>
                <dimension name="weight" xvalue="0.000000"/>
            </location>
        </source>
        <source filename="../sources/Bold/font.ufo" name="master_2">
            <location>
                <dimension name="weight" xvalue="1.000000"/>
            </location>
        </source>
    </sources>
    <instances>
        <instance familyname="MyFamily" filename="../instance/Medium.ufo" stylename="Medium">
            <location>
                <dimension name="weight" xvalue="0.500000"/>
            </location>
            <info/>
            <kerning/>
        </instance>
    </instances>
</designspace>
```

A more detailed description of the designspace format here: [designspace file format](designSpaceFileFormat.md)


### Writing a designspace

**DesignSpaceDocumentWriter** object writes an XML representation of a designspace.

* **addSource**(path, name, location, copyLib, copyGroups, copyInfo, muteKerning, muteInfo)
    *   **path**:           absolute path to the source UFO. Note: in the output the source path will relative to the documentPath. 
    *   **name**:           reference name for this source
    *   **location**:       name of the location for this UFO
    *   **copyLib**:        copy the contents of this source to instances
    *   **copyGroups**:     copy the groups of this source to instances
    *   **copyInfo**:       copy the non-numerical fields from this source.info to instances.
    *   **muteKerning**:    mute the kerning data from this source
    *   **muteInfo**:       mute the font info data from this source
* **startInstance**(name, familyName, styleName, fileName, postScriptFontName, styleMapFamilyName, styleMapStyleName)
    This starts a new current instance object.
    *   **name**: the name of this instance
    *   **familyName**: name for the font.info.familyName field. Required.
    *   **styleName**: name fot the font.info.styleName field. Required.
    *   **fileName**: absolute path for the instance UFO. Note: in the output the instance path will relative to the documentPath.
    *   **postScriptFontName**: name for the font.info.postScriptFontName field. Optional.
    *   **styleMapFamilyName**: name for the font.info.styleMapFamilyName field. Optional.
    *   **styleMapStyleName**: name for the font.info.styleMapStyleName field. Optional.
* **endInstance**()
    Finishes the current instance.
* **writeGlyph**(name, unicodeValue, location, masters)
    Add a new glyph to the current instance. 
    * **name**: the glyph name. Required.
    * **unicodeValue**: unicode value for this glyph if it needs to be different from the unicode value associated with this glyph name in the masters.
    * **location**: a design space location for this glyph if it needs to be different from the instance location. 
    * **masters**: a list of masters and locations for this glyph if they need to be different from the masters specified for this instance.
* **writeInfo()**: Indicate the info data should be generated for the current instance.
* **writeKerning()**: Indicate the kerning data should be generated for the current instance.

### Reading a designspace

**DesignSpaceDocumentReader** reads a DesignSpaceDocument. First it will look for all UFO masters and then it will build all instances.

* **DesignSpaceDocumentReader**(documentPath, ufoVersion, roundGeometry)
    *   **documentPath**:   path of the designspace document to read.
    *   **ufoVersion**:     target UFO version. Should be 2 or 3. 
    *   **roundGeometry**:  apply rounding to all geometry

DesignSpaceDocumentReader assumes all paths for sources and instances are relative to the documentPath.

## Legal

* **Superpolator** is a registered trademark of [LettError Type & Typography](http://letterror.com), More on [Superpolator.com](http://superpolator.com)

## Thanks

* MutatorMath was made possible with kind support from the Adobe Type Team. 
* Thanks to [TypeSupply](http://typesupply.com) for writing FontMath. 
* Thanks to [TypeMyType](http://robofont.com) for writing RoboFont. 
