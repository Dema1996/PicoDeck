import board
import digitalio
import supervisor
import usb_cdc
import adafruit_character_lcd.character_lcd as characterlcd

import state
import menus

lcd_rs = digitalio.DigitalInOut(board.GP2)
lcd_en = digitalio.DigitalInOut(board.GP3)
lcd_d4 = digitalio.DigitalInOut(board.GP4)
lcd_d5 = digitalio.DigitalInOut(board.GP5)
lcd_d6 = digitalio.DigitalInOut(board.GP6)
lcd_d7 = digitalio.DigitalInOut(board.GP7)
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, 16, 2)


def _pad16(s):
    s = s[:16]
    return s + " " * (16 - len(s))


def _print_lcd(line1, line2):
    if not supervisor.runtime.serial_connected:
        return
    try:
        msg = ("+----------------+\r\n"
               "|" + _pad16(line1) + "|\r\n"
               "|" + _pad16(line2) + "|\r\n"
               "+----------------+\r\n")
        usb_cdc.console.write(msg.encode())
    except OSError:
        pass


def draw_menu():
    lcd.clear()
    items = menus.get_menu_items(state.current_menu)
    item = items[state.selected_index]["label"]
    header = menus.get_menu_header(state.current_menu)
    counter = str(state.selected_index + 1) + "/" + str(len(items))
    line1 = header[:10] + " " + counter
    line2 = "> " + item
    lcd.message = line1[:16] + "\n" + line2[:16]
    _print_lcd(line1, line2)


def show_message(line1, line2=""):
    lcd.clear()
    lcd.message = line1[:16] + "\n" + line2[:16]
    _print_lcd(line1, line2)


def go_back():
    if state.menu_stack:
        state.current_menu = state.menu_stack.pop()
        state.selected_index = 0
        draw_menu()
