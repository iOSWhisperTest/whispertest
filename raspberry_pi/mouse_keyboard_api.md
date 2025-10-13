All requests are synchronous, meaning that they will only return a response once the action has been completed.

If a response includes `success: false`,
a `message` value may be included containing a human-readable string that indicates what went wrong.

# Generic endpoints

## `/status`

Returns the current USB connection status and mouse coordinates.

Arguments: None.

Example response:
```json
{
    "connected": true,
    "mouse_coordinates": [100, 200]
}
```

## `/open`

Opens the USB connection.

Arguments:\
`screen_size`: A list of two integers containing the screen size of the iOS device in pixels.
See https://www.ios-resolution.com/ (unaffiliated) for a convenient reference.

Example request:
```json
{
    "screen_size": [1080, 1920]
}
```

Example response:
```json
{
    "success": true
}
```

## `/close`

Closes the USB connection.

Arguments: None

Example response:
```json
{
    "success": true
}
```

# Keyboard endpoints

## `/keyboard/down`

Presses a single key on the virtual keyboard. Note that this endpoints works with keys and not characters:
For example, `!` cannot be pressed because it is not a single key,
but a combination of `shift_left` (or `shift_right`) and `1`.

Arguments:\
`key`: The key to press. Special values such as `enter` are allowed.

Example request:
```json
{
    "key": "a"
}
```

Example response:
```json
{
    "success": true
}
```

## `/keyboard/up`

Releases a single key on the virtual keyboard. Note that this endpoints works with keys and not characters:
For example, `!` cannot be released because it is not a single key,
but a combination of `shift_left` (or `shift_right`) and `1`.

Arguments:\
`key`: The key to release. Special values such as `enter` are allowed.

Example request:
```json
{
    "key": "a"
}
```

Example response:
```json
{
    "success": true
}
```

## `/keyboard/type`

A convenience endpoint that presses and releases keys to type out an arbitrary ASCII string.
This endpoint assumes that no keys are being pressed when it is called and that Caps Lock is off.

Arguments:\
`text`: The string to type.

Example request:
```json
{
    "text": "Hello, World!"
}
```

Example response:
```json
{
    "success": true
}
```

# Mouse endpoints

The virtual mouse has a left, middle, and right button and no scroll wheel.

## `/mouse/reset_coordinates`

Moves the virtual mouse to the top left corner of the screen and resets the internal coordinate tracker to `[0, 0]`.
This endpoint is mainly useful for debugging, since this action is automatically performed when calling `/open`.

Arguments: None.

Example response:
```json
{
    "success": true
}
```

## `/mouse/move`

Moves the virtual mouse to the specified coordinates.

Arguments:\
`target_coordinates`: A list of two integers containing the coordinates to move the mouse to in pixels.\
`mode` (optional): Specifies whether to interpret `target_coordinates` as absolute or as relative to the current mouse position.
    Accepted values are `absolute` and `relative`. Defaults to `absolute`.

Example request:
```json
{
    "target_coordinates": [100, 200],
    "mode": "relative"
}
```

Example response:
```json
{
    "success": true,
    "mouse_coordinates": [100, 200]
}
```

## `/mouse/down`

Presses a button on the virtual mouse.

Arguments:\
`button` (optional): The button to press. Accepted values are `left`, `middle`, and `right`. Defaults to `left`.

Example request:
```json
{
    "button": "right"
}
```

Example response:
```json
{
    "success": true
}
```

## `/mouse/up`

Releases a button on the virtual mouse.

Arguments:\
`button` (optional): The button to release. Accepted values are `left`, `middle`, and `right`. Defaults to `left`.

Example request:
```json
{
    "button": "right"
}
```

Example response:
```json
{
    "success": true
}
```
