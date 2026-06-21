import flet as ft
import random
import asyncio
import math
import os
import sys

# Check platform
IS_WEB = sys.platform in ["emscripten", "wasm32", "wasm64"]
# Mobile check will be performed inside main(page) using page.platform

# Flet App Globals for Flappy Bird
FPS = 32
SCREENWIDTH = 389
SCREENHEIGHT = 611
GROUNDY = SCREENHEIGHT * 0.8
# Handle paths for both script and PyInstaller EXE
if getattr(sys, 'frozen', False):
    # Running as a bundle (EXE)
    GALLERY_PATH = os.path.join(sys._MEIPASS, "assets")
else:
    # Running as a script
    GALLERY_PATH = os.path.join(os.path.dirname(__file__), "assets")

def main(page: ft.Page):
    # Determine platform
    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    is_desktop = not IS_WEB and not is_mobile

    # Debug Log for Audio (will show up at the bottom of the screen)
    debug_log = ft.Text(value="", color="red", size=10, weight="bold")
    
    # Audio Wrapper for Hybrid Support
    class Sound:
        def __init__(self, src):
            self.control = None
            self.pygame_sound = None
            
            # Use Native Browser Audio for Web/Mobile (Bypasses the broken Flet plugin)
            if page.web or is_mobile:
                self.js_src = src
            else:
                # Local Desktop App - Try Pygame
                try:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    path = os.path.join(GALLERY_PATH, src)
                    self.pygame_sound = pygame.mixer.Sound(path)
                except:
                    # If pygame fails on desktop, we just stay silent to avoid the red box
                    pass
        
        def play(self):
            try:
                if page.web or is_mobile:
                    # Tell the browser directly to play the sound (Native JS)
                    page.launch_url(f"javascript:new Audio('{self.js_src}').play()")
                elif self.pygame_sound:
                    self.pygame_sound.play()
            except Exception as e:
                debug_log.value = f"Play Error: {str(e)}"
                try: page.update()
                except: pass

    # Initialize Hybrid Audio
    hit_audio = Sound("audio/hit.wav")
    point_audio = Sound("audio/point.wav")
    wing_audio = Sound("audio/wing.wav")
    swoosh_audio = Sound("audio/swoosh.wav")
    
    # Final sync for audio controls
    if page.web or is_mobile:
        try:
            page.update()
        except: pass

    def unlock_audio_context():
        # Play a tiny silent sound to unlock the browser's audio context
        # This is a common requirement for web/mobile browsers
        for audio in [hit_audio, point_audio, wing_audio, swoosh_audio]:
            if audio.control:
                try:
                    audio.control.volume = 0 # Mute
                    audio.control.play()
                    # Reset volume after a tiny delay
                    audio.control.volume = 1.0
                except: pass
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    page.title = "Flappy Bird"
    # Using .ico for the best compatibility on Windows taskbar
    page.window.icon = "/icon.ico"
    page.fonts = {
        "FlappyFont": "fonts/FlappyFont.ttf",
        "PixelPurl": "fonts/PixelPurl.ttf"
    }
    # Flet window sizing limits
    page.window.resizable = True
    page.window.min_width = 200
    page.window.min_height = 300
    page.padding = 0
    page.spacing = 0
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.bgcolor = "black"
    
    # Physics settings
    playerMaxVelY = 10
    playerAccY = 1
    playerFlapAccv = -8
    pipeVelX = -4

    # Game State Variables
    state = {'current': 'start'} 
    is_transitioning = [False]
    score = [0]
    high_score = [0]
    playerVelY = [-9]
    player_x = int(SCREENWIDTH / 5)
    player_y = [165]
    player_x_start = (SCREENWIDTH + 240) / 2 + 10 

    # Pipes
    upper_pipes = []
    lower_pipes = []
    
    # Particle System
    particles = [] # List of dicts: {'control': ft.Container, 'vx': float, 'vy': float}
    
    def spawn_explosion(x, y, color):
        colors = [color] if isinstance(color, str) else color
        for _ in range(15):
            p_color = random.choice(colors)
            p_control = ft.Container(
                width=6, height=6,
                bgcolor=p_color,
                border_radius=1,
                left=x, top=y,
                opacity=1.0,
            )
            stack.controls.append(p_control)
            particles.append({
                'control': p_control,
                'vx': random.uniform(-6, 6),
                'vy': random.uniform(-9, 1)
            })

    # Load high score from client storage
    try:
        high_score[0] = page.client_storage.get("highscore") or 0
    except Exception:
        high_score[0] = 0
    
    def get_sprite(x, y, orig_w, orig_h, target_w, target_h, left=None, top=None, visible=True, animate_opacity=None, opacity=1.0, rotate=None, animate_rotation=None):
        scale_x = target_w / orig_w
        scale_y = target_h / orig_h
        return ft.Container(
            content=ft.Stack([
                ft.Image(
                    src="spriteSheet.png",
                    left=-x * scale_x,
                    top=-y * scale_y,
                    width=512 * scale_x,
                    height=512 * scale_y,
                    fit="fill",
                    filter_quality=ft.FilterQuality.NONE,
                )
            ]),
            width=target_w,
            height=target_h,
            left=left,
            top=top,
            visible=visible,
            opacity=opacity,
            animate_opacity=animate_opacity,
            rotate=rotate,
            animate_rotation=animate_rotation,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

    def get_animated_button(x, y, w, h, tw, th, left, top, on_click, visible=True):
        # Create the button sprite container
        sprite = get_sprite(x, y, w, h, tw, th, visible=visible)
        # Add a tiny animation for smooth movement
        sprite.animate_offset = ft.Animation(50, ft.AnimationCurve.EASE_OUT)
        
        def on_down(e):
            # Move down by 20% of its height for better visibility
            sprite.offset = ft.Offset(0, 0.15)
            try:
                sprite.update()
            except: pass
            
        async def on_up(e):
            if on_click:
                if asyncio.iscoroutinefunction(on_click):
                    await on_click(e)
                else:
                    on_click(e)
            
            # Move back to original position AFTER the delay
            sprite.offset = ft.Offset(0, 0)
            try:
                sprite.update()
            except: pass
            
        # Return a GestureDetector that moves the internal sprite
        return ft.GestureDetector(
            content=sprite,
            on_tap_down=on_down,
            on_tap_up=on_up,
            left=left,
            top=top
        )

    # Background frames (x, y)
    bg_frames = [
        (0, 0),    # Day
        (146, 0),  # Night
    ]
    # Sprites / UI Controls
    # Backup sky color to hide parallax gaps
    sky_backup = ft.Container(width=SCREENWIDTH, height=SCREENHEIGHT, bgcolor="#4ec0ca")
    # Using +5 width to ensure overlap and prevent "black line" gaps during scrolling
    bg_day = get_sprite(bg_frames[0][0], bg_frames[0][1], 144, 256, SCREENWIDTH + 5, SCREENHEIGHT, left=0, top=0, animate_opacity=800, opacity=1.0)
    bg_day2 = get_sprite(bg_frames[0][0], bg_frames[0][1], 144, 256, SCREENWIDTH + 5, SCREENHEIGHT, left=SCREENWIDTH, top=0, animate_opacity=800, opacity=1.0)
    
    bg_night = get_sprite(bg_frames[1][0], bg_frames[1][1], 144, 256, SCREENWIDTH + 5, SCREENHEIGHT, left=0, top=0, animate_opacity=800, opacity=0.0)
    bg_night2 = get_sprite(bg_frames[1][0], bg_frames[1][1], 144, 256, SCREENWIDTH + 5, SCREENHEIGHT, left=SCREENWIDTH, top=0, animate_opacity=800, opacity=0.0)
    
    # Parallax background velocity
    bg_vel = -0.5
    
    # Increased height to 185 to cover window bottom, and more aggressive crop (y=2, h=52) to remove green line
    base1 = get_sprite(292, 2, 168, 52, SCREENWIDTH + 5, 185, left=0, top=GROUNDY)
    base2 = get_sprite(292, 2, 168, 52, SCREENWIDTH + 5, 185, left=SCREENWIDTH, top=GROUNDY)
    
    # The message banner for Welcome screen (Get Ready + Tap-Tap) - scaled up
    message = ft.Container(
        content=ft.Column(
            controls=[
                get_sprite(295, 59, 92, 25, 246, 67),
                get_sprite(292, 91, 57, 49, 152, 131),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
        ),
        left=(SCREENWIDTH - 246) / 2,
        top=(SCREENHEIGHT - 218) / 2,
        visible=False
    )
    
    async def on_start_click(e):
        if is_transitioning[0]: return
        is_transitioning[0] = True
        
        # Unlock audio on first interaction
        unlock_audio_context()
        
        swoosh_audio.play()
        await fade_out()
        start_screen.visible = False
        message.visible = True
        state['current'] = 'welcome'
        # Position bird for welcome screen
        player_y[0] = int((SCREENHEIGHT - 24) / 2)
        bird.top = player_y[0]
        bird.left = player_x
        page.update()
        await fade_in()
        is_transitioning[0] = False

    start_screen = ft.Container(
        width=SCREENWIDTH,
        height=SCREENHEIGHT,
        visible=True,
        content=ft.Stack([
            ft.Container(
                top=160,
                left=(SCREENWIDTH - 240) / 2,
                content=get_sprite(351, 91, 89, 24, 240, 64)
            ),
            # Animated START Button - scaled up
            get_animated_button(354, 149, 38, 14, 102, 38, left=(SCREENWIDTH - 102) / 2, top=400, on_click=on_start_click)
        ])
    )
    
    # All bird colors from the sheet (Down, Mid, Up sequence)
    bird_variants = {
        'yellow': [(3, 491), (31, 491), (59, 491)],
        'blue': [(115, 355), (115, 329), (87, 491)],
        'red': [(115, 433), (115, 407), (115, 381)]
    }
    # We'll store the current frames in a list so we can modify it in-place
    bird_frames = [bird_variants['yellow']] 
    
    # Bird - scaled to exact 3x (51x36) to avoid sub-pixel glitching
    bird = get_sprite(
        bird_frames[0][0][0], bird_frames[0][0][1], 17, 12, 51, 36, 
        left=player_x_start, top=player_y[0],
        rotate=0,
        animate_rotation=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT)
    )
    
    # In-game score
    in_game_score = ft.Text(
        "0", size=60, font_family="FlappyFont", color=ft.Colors.WHITE, top=10, left=0, right=0, text_align=ft.TextAlign.CENTER, visible=False,
        style=ft.TextStyle(
            shadow=[
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(3, 3), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-3, 3), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(3, -3), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-3, -3), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(0, 3), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(0, -3), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(3, 0), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-3, 0), blur_radius=0),
            ]
        )
    )
    
    # Score Pop-up (+1) - Now using sprites
    score_plus_one = ft.Container(
        content=ft.Row(
            controls=[
                get_sprite(496, 84, 6, 6, 18, 18), # +
                get_sprite(141, 332, 4, 8, 12, 24), # 1
            ],
            spacing=2,
            alignment="center",
            vertical_alignment="center",
        ),
        width=40, height=30,
        opacity=0, top=0, left=0, visible=False,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        animate_position=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
    )
    
    # Flash overlay for collisions
    flash_overlay = ft.Container(
        left=-500,
        top=-500,
        width=2000,
        height=3000,
        bgcolor=ft.Colors.WHITE,
        opacity=0,
        visible=False,
        animate_opacity=ft.Animation(100, ft.AnimationCurve.EASE_OUT),
    )
    
    # Fade overlay for screen transitions
    fade_overlay = ft.Container(
        left=-500,
        top=-500,
        width=2000,
        height=3000,
        bgcolor=ft.Colors.BLACK,
        opacity=0,
        visible=False,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
    )

    game_over_score_val = ft.Text(
        "0", size=30, font_family="PixelPurl", color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER,
        style=ft.TextStyle(
            shadow=[
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(2, 2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-2, 2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(2, -2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-2, -2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(0, 2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(0, -2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(2, 0), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-2, 0), blur_radius=0),
            ]
        )
    )
    
    new_high_score_badge = get_sprite(112, 501, 16, 7, 43, 19, visible=False)
    
    game_over_hi_val = ft.Text(
        "0", size=30, font_family="PixelPurl", color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER,
        style=ft.TextStyle(
            shadow=[
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(2, 2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-2, 2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(2, -2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-2, -2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(0, 2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(0, -2), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(2, 0), blur_radius=0),
                ft.BoxShadow(color=ft.Colors.BLACK, offset=ft.Offset(-2, 0), blur_radius=0),
            ]
        )
    )

    medal_stack = ft.Stack([])
    # Using 15x15 (3x) for the final state (5x5 * 3 = 15)
    sparkle = get_sprite(139, 394, 5, 5, 15, 15, visible=False)
    
    def update_medal():
        medal_stack.controls.clear()
        # Use high_score for permanent medal memory
        hs = high_score[0]
        medal_sprite = None
        if hs >= 50:
            # Platinum
            medal_sprite = get_sprite(121, 258, 22, 22, 59, 59)
        elif hs >= 30:
            # Gold
            medal_sprite = get_sprite(121, 282, 22, 22, 59, 59)
        elif hs >= 20:
            # Silver
            medal_sprite = get_sprite(112, 453, 22, 22, 59, 59)
        elif hs >= 10:
            # Bronze
            medal_sprite = get_sprite(112, 477, 22, 22, 59, 59)
            
        if medal_sprite:
            medal_stack.controls.append(medal_sprite)
            # Add sparkle on top of the medal
            medal_stack.controls.append(sparkle)
            
    async def on_play_click(e):
        if is_transitioning[0]: return
        is_transitioning[0] = True
        
        # Ensure audio is unlocked
        unlock_audio_context()
        
        await fade_out()
        reset_to_start()
        await fade_in()
        is_transitioning[0] = False

    game_over_ui = ft.Container(
        visible=False,
        width=SCREENWIDTH,
        top=130,
        content=ft.Column(
            horizontal_alignment="center",
            spacing=15,
            controls=[
                ft.Container(
                    width=300, height=60,
                    alignment=ft.alignment.Alignment(0.0, 0.0),
                    content=get_sprite(395, 59, 96, 21, 260, 56)
                ),
                ft.Container(
                    width=305,
                    height=154,
                    content=ft.Stack([
                        # Scoreboard Sprite - scaled up
                        get_sprite(3, 259, 113, 57, 305, 154),
                        # Medal Slot
                        ft.Container(
                            content=medal_stack,
                            top=57,
                            left=35,
                        ),
                        # Score Value
                        ft.Container(
                            content=game_over_score_val,
                            top=44,
                            right=34,
                        ),
                        # High Score Value
                        ft.Container(
                            content=game_over_hi_val,
                            top=104,
                            right=34,
                        ),
                        # NEW badge - adjusted position
                        ft.Container(
                            content=new_high_score_badge,
                            top=100,
                            right=140,
                        ),
                    ])
                ),
                ft.Row(
                    alignment="center",
                    spacing=15,
                    controls=[
                        get_animated_button(462, 42, 40, 14, 110, 38, left=None, top=None, on_click=on_play_click)
                    ]
                )
            ]
        )
    )
    


    # Core Stack where all game elements live
    stack = ft.Stack(
        width=SCREENWIDTH, height=SCREENHEIGHT,
        controls=[
            sky_backup,
            bg_day,
            bg_day2,
            bg_night,
            bg_night2,
            message,
            start_screen,
            bird,
            base1,
            base2,
            in_game_score,
            score_plus_one,
            game_over_ui
        ]
    )

    def reset_to_start():
        state['current'] = 'start'
        game_over_ui.visible = False
        start_screen.visible = True
        message.visible = False
        in_game_score.visible = False
        
        # Position bird for start screen
        player_y[0] = 125
        bird.top = player_y[0]
        bird.left = player_x_start
        bird.rotate = 0
        
        # Smoothly fade the bird color change
        bird.opacity = 0.0
        try: page.update()
        except: pass
        
        # Pick a random bird color for the next run
        new_color = random.choice(['yellow', 'blue', 'red'])
        bird_frames[0] = bird_variants[new_color]
        
        # Update bird sprite immediately to show the new color
        bx, by = bird_frames[0][0]
        bird_img = bird.content.controls[0]
        bird_img.left = -bx * 3.0
        bird_img.top = -by * 3.0
        
        bird.opacity = 1.0
        try: page.update()
        except: pass
        
        # Reset score
        score[0] = 0
        in_game_score.value = "0"
        new_high_score_badge.visible = False
        # We no longer clear medal_stack here for permanent memory
        
        # Clean pipes
        for p in upper_pipes + lower_pipes:
            if p in stack.controls:
                stack.controls.remove(p)
        upper_pipes.clear()
        lower_pipes.clear()
        
        # Reset backgrounds to Day and loop positions
        bg_day.left = 0
        bg_day2.left = SCREENWIDTH
        bg_day.opacity = 1.0
        bg_day2.opacity = 1.0
        
        bg_night.left = 0
        bg_night2.left = SCREENWIDTH
        bg_night.opacity = 0.0
        bg_night2.opacity = 0.0
        
        try:
            page.update()
        except: pass

    async def fade_out():
        fade_overlay.opacity = 0.0
        fade_overlay.visible = True
        page.update()
        await asyncio.sleep(0.05)
        fade_overlay.opacity = 1.0
        page.update()
        await asyncio.sleep(0.3)

    async def fade_in():
        fade_overlay.opacity = 0.0
        page.update()
        await asyncio.sleep(0.3)
        fade_overlay.visible = False
        page.update()

    async def start_game():
        if is_transitioning[0]: return
        is_transitioning[0] = True
        await fade_out()
        state['current'] = 'playing'
        message.visible = False
        game_over_ui.visible = False
        in_game_score.visible = True
        
        player_y[0] = int(SCREENWIDTH / 2)
        playerVelY[0] = -9
        score[0] = 0
        in_game_score.value = "0"
        
        # Reset background to Day
        bg_day.opacity = 1.0
        bg_night.opacity = 0.0
        
        # Clean pipes
        for p in upper_pipes + lower_pipes:
            if p in stack.controls:
                stack.controls.remove(p)
        upper_pipes.clear()
        lower_pipes.clear()
        
        # Add initial pipes
        u1, l1 = generate_pipes(SCREENWIDTH + 200)
        u2, l2 = generate_pipes(SCREENWIDTH + 200 + (SCREENWIDTH / 2))
        upper_pipes.extend([u1, u2])
        lower_pipes.extend([l1, l2])
        
        # Insert them behind the base but in front of background
        for p in [u1, l1, u2, l2]:
            stack.controls.insert(5, p)
            
        page.update()
        is_transitioning[0] = False
        await fade_in()

    def generate_pipes(pipeX):
        pipeHeight = 384 # Scaled pipe height
        offset = SCREENHEIGHT / 3
        y2 = offset + random.randrange(0, int(SCREENHEIGHT - 115 - 1.2 * offset))
        y1 = pipeHeight - y2 + offset
        
        # Determine theme based on current score
        is_night = ((score[0] // 10) % 2) == 1
        
        if is_night:
            # Orange/Red pipes (both point UP in this sheet, so top needs rotation)
            top_px, top_py = 0, 323
            bot_px, bot_py = 28, 323
            u_rot = math.pi
        else:
            # Green pipes (top points DOWN, bottom points UP natively)
            top_px, top_py = 56, 323
            bot_px, bot_py = 84, 323
            u_rot = None
            
        # Scaled pipes
        u_pipe = get_sprite(top_px, top_py, 26, 160, 70, 384, left=pipeX, top=-y1, rotate=u_rot)
        l_pipe = get_sprite(bot_px, bot_py, 26, 160, 70, 384, left=pipeX, top=y2)
        return u_pipe, l_pipe

    def intersect(x1, y1, w1, h1, x2, y2, w2, h2):
        return (x1 < x2 + w2 and
                x1 + w1 > x2 and
                y1 < y2 + h2 and
                y1 + h1 > y2)

    def check_collision():
        # Floor or Ceiling - Using .1 epsilon to ensure floating point hits the ground reliably
        if player_y[0] >= GROUNDY - 36.1 or player_y[0] < 0:
            return True
        for up_pipe in upper_pipes:
            if intersect(player_x, player_y[0], 51, 36, up_pipe.left, up_pipe.top, 70, 384):
                return True
        for low_pipe in lower_pipes:
            if intersect(player_x, player_y[0], 51, 36, low_pipe.left, low_pipe.top, 70, 384):
                return True
        return False

    def show_game_over():
        state['current'] = 'gameover'
        is_new_high = score[0] > high_score[0]
        
        if is_new_high:
            high_score[0] = score[0]
            new_high_score_badge.visible = True
            try:
                page.client_storage.set("highscore", score[0])
            except: pass
        else:
            new_high_score_badge.visible = False
        
        game_over_score_val.value = str(score[0])
        game_over_hi_val.value = str(high_score[0])
        game_over_ui.visible = True
        in_game_score.visible = False
        
        # Update permanent medal
        update_medal()
            
        try:
            page.update()
        except: pass

    async def handle_flap():
        if is_transitioning[0]: return
        if state['current'] == 'playing':
            if player_y[0] > 0:
                playerVelY[0] = playerFlapAccv
                wing_audio.play()
        elif state['current'] == 'welcome':
            await start_game()

    async def on_keyboard(e: ft.KeyboardEvent):
        if e.key == "Escape":
            page.window.destroy()
        elif e.key in [" ", "Arrow Up"]:
            await handle_flap()

    async def on_click(e):
        # Just simple flap check
        await handle_flap()

    page.on_keyboard_event = on_keyboard
    
    page.on_keyboard_event = on_keyboard
    
    # Master Stack to cover the whole window
    master_stack = ft.Stack(
        width=SCREENWIDTH,
        height=2000, # Large height to prevent clipping overlays at the bottom
        controls=[
            ft.Container(
                content=stack,
                width=SCREENWIDTH,
                height=SCREENHEIGHT,
                on_click=on_click,
            ),
            flash_overlay,
            fade_overlay
        ]
    )

    # Game Container to handle responsive scaling
    game_container = ft.Container(
        content=master_stack,
        width=SCREENWIDTH,
        height=SCREENHEIGHT,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    
    # Use a Stack as the root to allow manual positioning and avoid layout clipping
    root_stack = ft.Stack(
        controls=[game_container],
        expand=True,
    )

    # Resize function to scale the game to fit the window
    def resize_game(e=None):
        if not page.width or not page.height:
            return
            
        # Calculate scale factor based on available space
        # Use a small safety margin (0.98) to avoid touching window edges
        scale = min(page.width / SCREENWIDTH, page.height / SCREENHEIGHT) * 0.98
        game_container.scale = scale
        
        # Manually center the container in the stack
        # This prevents the container from being clipped by layout overflow
        game_container.left = (page.width - SCREENWIDTH) / 2
        game_container.top = (page.height - SCREENHEIGHT) / 2
        
        # Position debug log at the bottom
        debug_log.bottom = 10
        debug_log.left = 10
        
        try:
            page.update()
        except: pass

    page.on_resize = resize_game
    page.overlay.append(debug_log)
    page.add(root_stack)
    
    # Trigger initial resize
    resize_game()

    async def game_loop():
        frame_index = 0
        frame_tick = 0
        sparkle_tick = 0
        
        while True:
            if state['current'] == 'gameover':
                # Animate sparkles for Gold/Platinum medals
                if high_score[0] >= 10:
                    sparkle_tick += 1
                    if sparkle_tick >= 6: # Faster shimmer
                        sparkle_tick = 0
                        
                        # The 3 states provided by the user (x, y, w, h)
                        sf_frames = [
                            (141, 344, 1, 1), # Initial
                            (140, 369, 3, 3), # Mid
                            (139, 394, 5, 5)  # Final
                        ]
                        
                        # Animation state sequence: 0 -> 1 -> 2 -> 1 -> repeat
                        if not hasattr(game_loop, 's_frame'): game_loop.s_frame = 0
                        if not hasattr(game_loop, 's_dir'): game_loop.s_dir = 1
                        
                        game_loop.s_frame += game_loop.s_dir
                        if game_loop.s_frame >= 2: game_loop.s_dir = -1
                        if game_loop.s_frame <= 0: 
                            game_loop.s_dir = 1
                            # Move to a new random spot when we restart the pulse
                            sparkle.left = random.randint(5, 42)
                            sparkle.top = random.randint(5, 42)
                        
                        sf_x, sf_y, sf_w, sf_h = sf_frames[game_loop.s_frame]
                        sparkle.visible = True
                        
                        # Update sparkle internal sprite with centering
                        s_img = sparkle.content.controls[0]
                        center_off_x = (15 - sf_w * 3.0) / 2
                        center_off_y = (15 - sf_h * 3.0) / 2
                        s_img.left = (-sf_x * 3.0) + center_off_x
                        s_img.top = (-sf_y * 3.0) + center_off_y
                else:
                    sparkle.visible = False
            
            if state['current'] in ['playing', 'welcome', 'start']:
                # Bird Animation (Flapping)
                frame_tick += 1
                if frame_tick >= 4:
                    frame_tick = 0
                    frame_index = (frame_index + 1) % len(bird_frames[0])
                    
                    bx, by = bird_frames[0][frame_index]
                    bx, by = bird_frames[0][frame_index]
                    bird_img = bird.content.controls[0]
                    # Back to integer 3.0 scale to fix the glitches
                    bird_img.left = -bx * 3.0
                    bird_img.top = -by * 3.0
                
                # Move Background (Parallax)
                bg_day.left += bg_vel
                bg_day2.left += bg_vel
                bg_night.left += bg_vel
                bg_night2.left += bg_vel
                
                if bg_day.left <= -SCREENWIDTH:
                    bg_day.left = bg_day2.left + SCREENWIDTH
                    bg_night.left = bg_night2.left + SCREENWIDTH
                if bg_day2.left <= -SCREENWIDTH:
                    bg_day2.left = bg_day.left + SCREENWIDTH
                    bg_night2.left = bg_night.left + SCREENWIDTH
                
                # Move Base
                base1.left += pipeVelX
                base2.left += pipeVelX
                if base1.left <= -SCREENWIDTH:
                    base1.left = base2.left + SCREENWIDTH
                if base2.left <= -SCREENWIDTH:
                    base2.left = base1.left + SCREENWIDTH
                
                if state['current'] in ['welcome', 'start']:
                    pass # Handled by final update

            if state['current'] == 'playing':
                # Apply Gravity
                if playerVelY[0] < playerMaxVelY:
                    playerVelY[0] += playerAccY
                
                # Apply velocity
                player_y[0] = min(player_y[0] + playerVelY[0], GROUNDY - 36)
                bird.top = player_y[0]
                
                # Bird Rotation
                if playerVelY[0] < 0:
                    # Flapping up
                    bird.rotate = -math.pi / 6
                else:
                    # Falling down
                    bird.rotate = min(math.pi / 2, playerVelY[0] * 0.15)
                
                # Move Pipes
                for up_pipe, low_pipe in zip(upper_pipes, lower_pipes):
                    up_pipe.left += pipeVelX
                    low_pipe.left += pipeVelX
                    
                # Remove left-out pipes and add new ones
                # Remove left-out pipes and add new ones (70 is new pipe width)
                if len(upper_pipes) > 0 and upper_pipes[0].left < -70:
                    p_u = upper_pipes.pop(0)
                    p_l = lower_pipes.pop(0)
                    if p_u in stack.controls:
                        stack.controls.remove(p_u)
                    if p_l in stack.controls:
                        stack.controls.remove(p_l)

                if len(upper_pipes) > 0 and 0 < upper_pipes[0].left < 5:
                    new_u, new_l = generate_pipes(SCREENWIDTH + 10)
                    upper_pipes.append(new_u)
                    lower_pipes.append(new_l)
                    stack.controls.insert(5, new_u)
                    stack.controls.insert(5, new_l)
                
                # Score update checking
                for up_pipe in upper_pipes:
                    pipeMidPos = up_pipe.left + 35
                    playerMidPos = player_x + 21
                    # Using range to ensure we score exactly once when crossing
                    if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                        score[0] += 1
                        point_audio.play()
                        in_game_score.value = str(score[0])
                        
                        # Show +1 Popup (Non-blocking background task)
                        async def animate_plus_one():
                            is_new_high = score[0] > high_score[0]
                            
                            # Gold glow for new high score
                            score_plus_one.content.controls[0].bgcolor = "#f6ce46" if is_new_high else None
                            
                            score_plus_one.left = player_x + 60
                            score_plus_one.top = player_y[0]
                            score_plus_one.opacity = 1.0
                            score_plus_one.visible = True
                            
                            if is_new_high:
                                # Fireworks!
                                spawn_explosion(player_x + 60, player_y[0], ["#f6ce46", "#ffffff", "#ff0000", "#00ff00"])
                                
                            try:
                                page.update()
                                await asyncio.sleep(0.1)
                                score_plus_one.top -= 60
                                score_plus_one.opacity = 0.0
                                page.update()
                                await asyncio.sleep(0.5)
                                score_plus_one.visible = False
                            except: pass
                            
                        asyncio.create_task(animate_plus_one())
                        
                        # Update background crossfade based on score
                        bg_index = (score[0] // 10) % 2
                        if bg_index == 0:
                            bg_day.opacity = 1.0
                            bg_day2.opacity = 1.0
                            bg_night.opacity = 0.0
                            bg_night2.opacity = 0.0
                        else:
                            bg_day.opacity = 0.0
                            bg_day2.opacity = 0.0
                            bg_night.opacity = 1.0
                            bg_night2.opacity = 1.0
                
                # Collisions
                if check_collision():
                    hit_audio.play()
                    
                    # Determine explosion color based on what we hit
                    p_color = "#ded895" # Ground default
                    if player_y[0] < GROUNDY - 40:
                        # Likely hit a pipe
                        p_color = "#558022" if ((score[0] // 10) % 2) == 0 else "#e86101"
                    
                    spawn_explosion(player_x + 25, player_y[0] + 18, p_color)
                    
                    # Trigger Flash
                    flash_overlay.visible = True
                    flash_overlay.opacity = 1.0
                    
                    # Small delay for flash visibility before reset flash
                    await asyncio.sleep(0.05)
                    flash_overlay.opacity = 0.0
                    
                    if player_y[0] < GROUNDY - 36.1:
                        # Hit a pipe, start falling sequence
                        state['current'] = 'falling'
                        playerVelY[0] = 0 # stop current momentum
                    else:
                        # Hit ground directly
                        show_game_over()
                    
                    # Hide flash overlay after it fades out (100ms animation)
                    await asyncio.sleep(0.1)
                    flash_overlay.visible = False
                    
                    try:
                        page.update()
                    except: break

                pass # Handled by final update
            
            elif state['current'] == 'falling':
                # Apply heavier Gravity for falling sequence
                playerVelY[0] += 2
                player_y[0] = min(player_y[0] + playerVelY[0], GROUNDY - 36)
                bird.top = player_y[0]
                # Nose-dive rotation
                bird.rotate = math.pi / 2
                
                if player_y[0] >= GROUNDY - 36.1:
                    # Hit the ground
                    show_game_over()
                
                pass # Handled by final update
                
            # Update Particles (Physics)
            for p in particles[:]:
                p['vx'] *= 0.95 # friction
                p['vy'] += 0.6 # gravity
                p['control'].left += p['vx']
                p['control'].top += p['vy']
                p['control'].opacity = max(0, p['control'].opacity - 0.05)
                
                if p['control'].opacity <= 0:
                    try:
                        stack.controls.remove(p['control'])
                    except: pass
                    particles.remove(p)
            
            # Global Single Page Update (fixes lag on web)
            try:
                page.update()
            except:
                break
                
            await asyncio.sleep(1/FPS)

    # Start the async background task
    page.run_task(game_loop)

# Using standard assets_dir mapping
ft.app(main, assets_dir="assets")
