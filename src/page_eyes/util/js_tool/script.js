const script = {
    add_highlight_element: ([bbox]) => {
        let box = document.querySelector("#option-el-box")
        if (!box) {
            box = document.createElement("div")
            box.id = "option-el-box"
            box.style.position = "absolute"
            box.style.zIndex = "1000"
            box.style.border = "2px solid rgba(255,0,0)"
            box.style.borderRadius = "5px"
            box.style.pointerEvents = "none"
            document.body.appendChild(box)
        }
        const [x1, y1, x2, y2] = bbox
        box.style.top = y1 * 100 + "%"
        box.style.left = x1 * 100 + "%"
        box.style.width = (x2 - x1) * 100 + "%"
        box.style.height = (y2 - y1) * 100 + "%"
        return box
    },
    remove_highlight_element: () => {
        const box = document.querySelector("#option-el-box");
        if (box) {
            box.remove();
        }
    },
    add_highlight_position: ([x, y]) => {
        let position = document.querySelector("#option-el-position")
        if (!position) {
            position = document.createElement("div")
            position.id = "option-el-position"
            position.style.position = "absolute"
            position.style.zIndex = "1000"
            position.style.height = "10px"
            position.style.width = "10px"
            position.style.background = "red"
            position.style.borderRadius = "50%"
            position.style.pointerEvents = "none"
            document.body.appendChild(position)
        }
        position.style.left = `${x}px`
        position.style.top = `${y}px`
        return position
    },
    remove_highlight_position: () => {
        const position = document.querySelector("#option-el-position");
        if (position) {
            position.remove();
        }
    },
    has_vertical_scrollbar: () => document.body.scrollHeight > window.innerHeight,
    has_horizontal_scrollbar: () => document.body.scrollWidth > window.innerWidth,

}