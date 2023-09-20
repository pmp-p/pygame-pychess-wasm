import pygbag.aio as asyncio
import pygame
import sys
from src.const import *
from src.game import Game
from src.square import Square
from src.move import Move

pygame.init()
# import pygame.freetype
# pygame.font.init()
# pygame.freetype.init()

import pygbag_net


class Node(pygbag_net.Node):
    ...


builtins.node = Node(gid=666, offline="offline" in sys.argv)


class Main:
    def __init__(self):
        # self.screen = pygame.display.set_mode( (WIDTH, HEIGHT), pygame.NOFRAME)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), 0)
        pygame.display.set_caption("Chess")
        self.game = Game()

    def make_move(self, piece, move, dragger=None):
        #
        screen = self.screen
        game = self.game
        board = self.game.board

        # normal capture
        if dragger:
            released_row = dragger.mouseY // SQSIZE
            released_col = dragger.mouseX // SQSIZE

            captured = board.squares[released_row][released_col].has_piece()

            # transmit to hub
            txdata = move.export()
            txdata["color"] = piece.color
            node.tx(txdata)

        board.move(piece, move)

        if dragger:
            board.set_true_en_passant(dragger.piece)
            # sounds
            game.play_sound(captured)

        # show methods
        game.show_bg(screen)
        game.show_last_move(screen)
        game.show_pieces(screen)
        # next turn
        game.next_turn()

    async def mainloop(self):
        screen = self.screen
        game = self.game
        board = self.game.board
        dragger = self.game.dragger

        while True:
            for ev in node.get_events():
                if ev == node.LOBBY:
                    print("LOBBY:", node.data)
                elif ev == node.GAME:
                    print("GAME:", node.proto, node.data)

                    grid_from, grid_to = node.data.pop("from"), node.data.pop("to")
                    gfrom = Square(grid_from[1], grid_from[0])
                    gto = Square(grid_to[1], grid_to[0])
                    piece = board.squares[gfrom.row][gfrom.col].piece
                    self.make_move(piece, Move(gfrom, gto), dragger=None)

                elif ev == node.RAW:
                    print("RAW:", node.data)
                elif ev == node.PING:
                    print("ping", node.data)
                elif ev == node.PONG:
                    print("pong", node.data)
                elif ev == node.RX:
                    ...
                else:
                    print(f"52:{ev=} {node.rxq=}")

            # show methods
            game.show_bg(screen)
            game.show_last_move(screen)
            game.show_moves(screen)
            game.show_pieces(screen)
            game.show_hover(screen)

            if dragger.dragging:
                dragger.update_blit(screen)

            for event in pygame.event.get():
                # click
                if event.type == pygame.MOUSEBUTTONDOWN:
                    dragger.update_mouse(event.pos)

                    clicked_row = dragger.mouseY // SQSIZE
                    clicked_col = dragger.mouseX // SQSIZE

                    # if clicked square has a piece ?
                    if board.squares[clicked_row][clicked_col].has_piece():
                        piece = board.squares[clicked_row][clicked_col].piece
                        # valid piece (color) ?
                        if piece.color == game.next_player:
                            board.calc_moves(piece, clicked_row, clicked_col, bool=True)
                            dragger.save_initial(event.pos)
                            dragger.drag_piece(piece)
                            # show methods
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)

                # mouse motion
                elif event.type == pygame.MOUSEMOTION:
                    motion_row = event.pos[1] // SQSIZE
                    motion_col = event.pos[0] // SQSIZE

                    game.set_hover(motion_row, motion_col)

                    if dragger.dragging:
                        dragger.update_mouse(event.pos)
                        # show methods
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)
                        game.show_hover(screen)
                        dragger.update_blit(screen)

                # click release
                elif event.type == pygame.MOUSEBUTTONUP:
                    if dragger.dragging:
                        dragger.update_mouse(event.pos)

                        released_row = dragger.mouseY // SQSIZE
                        released_col = dragger.mouseX // SQSIZE

                        # create possible move
                        initial = Square(dragger.initial_row, dragger.initial_col)
                        final = Square(released_row, released_col)
                        move = Move(initial, final)

                        # valid move ?
                        if board.valid_move(dragger.piece, move):
                            self.make_move(dragger.piece, move, dragger=dragger)

                    dragger.undrag_piece()

                # key press
                elif event.type == pygame.KEYDOWN:
                    # changing themes
                    if event.key == pygame.K_t:
                        game.change_theme()

                    if event.key == pygame.K_r:
                        game.reset()
                        game = self.game
                        board = self.game.board
                        dragger = self.game.dragger

                    if event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()

                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            pygame.display.update()
            await asyncio.sleep(0)


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.mainloop())
