# modifierCacheAddon
blender addon to add modifiers on all object types and bake them into alembic sequence 


## Install

1. Download the add-on:
    [Download modifierCacheAddon.zip](https://github.com/icalvin102/modifierCacheAddon/archive/master.zip)
2. Open `Edit` → `Preferences` → `Add-ons` category.
3. Use `Install` to install the downloaded .zip file.


## Usage

The addon adds `Mesh Override` and `Modifier Cache` to the `Modifiers`-Panel.

### Mesh Override 

`Mesh Override`: If enabled the option will override the current the mesh with the `Override Object`

`Override Object`: Object of type Mesh, Curve, Text, Surface or Metaball

`Use Modifiers`: Wether or not to apply the Modifier-stack of the `Override Object`.

    can lead to interesting feedback behaviour if the `Override Object` is the Object itself.
    
    (has to be enabled when using Metaballs)
    

### Modifier Cache

`Frame Start`: Start frame of the cache

`Frame End`: End frame of the cache

`Filepath`: Filepath of the Alembic cache sequence. (Framenumber and fileextension will be added automatically)

`Bake Cache`: Bake cache to a sequence of Alembic files

`Free Cache`: Hide bake

`Apply Cache`: Applies Cache as a 'Mesh Seqence Cache'-Modifier
