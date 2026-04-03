import tkinter as tk

def select_screen_area():
    """
    Creates a full-screen transparent window allowing the user to click and drag 
    to select a bounding box. Returns a dictionary with top, left, width, height.
    """
    root = tk.Tk()
    
    # Make the window transparent and cover the whole screen
    root.attributes('-alpha', 0.4)
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(bg='black', cursor="cross")

    canvas = tk.Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    rect = None
    start_x = start_y = 0
    end_x = end_y = 0

    message = canvas.create_text(
        root.winfo_screenwidth() // 2, 
        50, 
        text="Click and drag to select your Minimap. Press ESC to use default.", 
        fill="white", 
        font=("Arial", 20, "bold")
    )

    def on_button_press(event):
        nonlocal start_x, start_y, rect
        start_x = event.x
        start_y = event.y
        # Create a rectangle with a reddish overlay
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=3, fill="red", stipple="gray50")

    def on_move_press(event):
        nonlocal rect
        if rect:
            canvas.coords(rect, start_x, start_y, event.x, event.y)

    def on_button_release(event):
        nonlocal end_x, end_y
        end_x = event.x
        end_y = event.y
        root.quit()

    def on_escape(event):
        nonlocal start_x, end_x
        start_x = end_x = None  # Signal cancellation
        root.quit()

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move_press)
    canvas.bind("<ButtonRelease-1>", on_button_release)
    root.bind("<Escape>", on_escape)

    root.mainloop()

    if start_x is not None and end_x is not None:
        left = min(start_x, end_x)
        top = min(start_y, end_y)
        width = abs(start_x - end_x)
        height = abs(start_y - end_y)
        root.destroy()
        
        if width > 10 and height > 10:
            return {'top': top, 'left': left, 'width': width, 'height': height}
    
    root.destroy()
    return None

if __name__ == '__main__':
    print("Testing selector...")
    area = select_screen_area()
    print("Selected:", area)
