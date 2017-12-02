[[Readme in Japanese (日本語)](./README_ja.md)]

---

# Circle N

Blender Addon # An axis-free manipulator with circle based GUI

> [**Download circle_n.zip**]()

![image](./doc/a.jpg)


## Installation
1. `Blender User Preference` > `Install from File` > Select `circle_n.zip`
2. Activate `3D View: Circle N` in Addons Preference

## Usage

![image](./doc/b.gif)

This addon supports following edit modes in 3D View:
- Object mode
- Edit mode of Mesh/Curve/Arumature
- Pose mode

Selecting subject(s) in above modes (e.g. objects in Object mode, vertices/edges/faces in Edit Mesh mode),
pressing the buttons `Move` `Rotate` `Scale` in Circle N panel or pressing hotkey starts CircleN.
Default hotkey is `Q`, and it starts `Move` mode.

![image](./doc/panel.jpg) <br>
*(3D View) Circle N Panel*

### Common manipulation on each mode
- `Mouse Move` : Set the direction of CircleN
- `Mouse Right Drag` / `Shift + Mouse Right Drag` : Transform the subjects through the direction depending on current mode (see below)
- `Mouse Left Click` : Confirm & Exit
- `Esc` key : Cancel
- `C` key : Capture -- Set the CircleN direction on an object face normal of under mouse cursor (see below)
- `Q` key : Toggle current mode in order of `Move` -> `Rotate` -> `Scale` -> `Move` ...
- `G` `R` `S` key : Switch current mode to `Move` `Rotate` `Scale`

---

### `Move` mode

Move the subject(s).

- `Mouse Right Drag` : Translate toward CircleN direction

  ![image](./doc/move1.gif)

- `Shift + Mouse Right Drag` : Translate on the plane which is orthogonal to CircleN direction

  ![image](./doc/move2.gif)

---

### `Rotate` mode

Rotate the subject(s).

- `Mouse Right Drag` : Following mouse drag, the CircleN direction changes, and the subjects are rotated in a form fixed to the direction

  ![image](./doc/rot1.gif)

- `Shift + Mouse Right Drag` : Rotate around the direction

  ![image](./doc/rot2.gif)

---

### `Scale` mode

Scale the subject(s).

- `Mouse Right Drag` : Scale toward the direction

  ![image](./doc/scale1.gif)

- `Shift + Mouse Right Drag` : Scale on the plane which is orthogonal to CircleN direction

  ![image](./doc/scale2.gif)


---

### Capture

Pressing `C` key executes the `Capture Normal`.
the direction will be set on an object face normal direction of under mouse cursor.

![image](./doc/capt1.gif)

When execute the capture in `Rotate` mode, only `Rotate around the direction` method is enabled.
(`Mouse Right Drag` will equal to `Shift + Mouse Right Drag`)

