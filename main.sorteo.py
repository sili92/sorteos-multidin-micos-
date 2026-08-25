import random

class BuscaminasAdmin:
    def __init__(self, filas=5, columnas=5, num_bombas=3, num_podridas=2):
        self.filas = filas
        self.columnas = columnas
        self.num_bombas = num_bombas
        self.num_podridas = num_podridas
        self.tablero = []
        self.visibles = []
        self.inicializar_tablero()

    def inicializar_tablero(self):
        """Crea un tablero nuevo y distribuye bombas normales y podridas."""
        self.tablero = [['vacío' for _ in range(self.columnas)] for _ in range(self.filas)]
        self.visibles = [['?' for _ in range(self.columnas)] for _ in range(self.filas)]
        
        # Colocar bombas normales ('X')
        posiciones = [(r, c) for r in range(self.filas) for c in range(self.columnas)]
        bombas = random.sample(posiciones, self.num_bombas)
        for r, c in bombas:
            self.tablero[r][c] = 'X'
            posiciones.remove((r, c))
            
        # Colocar bombas podridas ('P')
        podridas = random.sample(posiciones, self.num_podridas)
        for r, c in podridas:
            self.tablero[r][c] = 'P'

    def mostrar_tablero(self):
        for fila in self.visibles:
            print(" ".join(fila))
        print("-" * 15)

    def seleccionar_casilla(self, fila, col):
        """Procesa la jugada en base al tipo de casilla."""
        contenido = self.tablero[fila][col]
        
        if contenido == 'X':
            print("💥 ¡BOOM! Ha explotado una bomba normal.")
            print("🔄 Reiniciando el tablero por completo...\n")
            self.inicializar_tablero()
            return "EXPLOSION_REINICIO"

        elif contenido == 'P':
            self.visibles[fila][col] = 'P'
            print("🤢 ¡Has destapado una Bomba Podrida!")
            print("⚠️ Pierdes puntos/turno, pero la partida continúa y el tablero NO se reinicia.\n")
            return "PODRIDA"

        else:
            self.visibles[fila][col] = 'O'
            print("✅ Casilla segura.\n")
            return "SEGURO"

    def notificar_instrucciones_admin(self, admin_nombre):
        """Genera y envía las instrucciones del sistema al administrador."""
        mensaje = f"""
==================================================
  INSTRUCCIONES DE SISTEMA PARA ADMIN: {admin_nombre.upper()}
==================================================

1. REINICIO POR EXPLOSIÓN:
   - Si un jugador activa una bomba normal ('X'), el tablero 
     explotará y se REINICIARÁ automáticamente por completo.

2. FUNCIONAMIENTO DE LA OPCIÓN 'PODRIDA' ('P'):
   - Regla: No hace explotar el tablero ni reinicia la partida.
   - Penalización: El jugador sufre castigo de puntos o pérdida 
     de turno.
   - Estado: La casilla queda marcada como 'P' y el juego continúa 
     con el resto de casillas intactas.
==================================================
        """
        print(mensaje)
        return mensaje


# --- EJEMPLO DE USO ---
if __name__ == "__main__":
    juego = BuscaminasAdmin(filas=4, columnas=4, num_bombas=2, num_podridas=2)

    # 1. El bot/sistema notifica al administrador las reglas
    juego.notificar_instrucciones_admin("Carlos_Admin")

    # 2. Simulación de partida
    print("Estado inicial del tablero:")
    juego.mostrar_tablero()

    # Probar una casilla (ejemplo: fila 0, columna 0)
    print("Jugador selecciona (0, 0):")
    resultado = juego.seleccionar_casilla(0, 0)
    
    juego.mostrar_tablero()
