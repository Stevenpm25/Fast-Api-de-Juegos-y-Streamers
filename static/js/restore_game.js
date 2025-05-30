// Function to show the restore form
function showRestoreForm() {
    hideAllForms();
    
    // Check if the form already exists
    let restoreForm = document.getElementById('restoreForm');
    
    // If the form doesn't exist, create it
    if (!restoreForm) {
        const formHTML = `
        <div id="restoreForm" class="operation-form rpgui-container framed-golden" style="display: none;">
            <h3>♻️ Recuperar Juego Eliminado</h3>
            <form onsubmit="restoreGame(event)">
                <div class="form-group">
                    <label class="rpgui-label">🔢 ID del Juego:</label>
                    <input type="number" id="restoreGameId" class="rpgui-input" required min="1">
                </div>
                <div class="form-buttons">
                    <button type="submit" class="rpgui-button">
                        <span>♻️ Recuperar</span>
                    </button>
                    <button type="button" class="rpgui-button" onclick="hideAllForms()">
                        <span>❌ Cancelar</span>
                    </button>
                </div>
            </form>
        </div>
        `;
        
        // Add the form to the forms container
        const formsContainer = document.querySelector('.forms-container');
        formsContainer.insertAdjacentHTML('beforeend', formHTML);
        
        // Get the newly created form
        restoreForm = document.getElementById('restoreForm');
    }
    
    // Show the form
    restoreForm.style.display = 'block';
}

// Function to restore a deleted game
async function restoreGame(event) {
    event.preventDefault();
    const gameId = document.getElementById('restoreGameId').value;

    if (confirm('¿Estás seguro de que deseas recuperar este juego eliminado?')) {
        try {
            const response = await fetch(`/api/games/recover/${gameId}`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('¡Juego recuperado correctamente!');
                location.reload();
            } else {
                const error = await response.json();
                alert('Error al recuperar el juego: ' + error.detail);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error al recuperar el juego');
        }
    }
}

// Function to show deleted games
async function showDeletedGames() {
    try {
        const response = await fetch('/api/games/deleted');
        if (response.ok) {
            const deletedGames = await response.json();
            hideAllForms();

            if (deletedGames.length === 0) {
                alert('No hay juegos eliminados para mostrar');
                return;
            }

            // Check if the form already exists
            let deletedGamesForm = document.getElementById('deletedGamesForm');
            
            // If the form exists, remove it
            if (deletedGamesForm) {
                deletedGamesForm.remove();
            }

            const tableHTML = `
                <div id="deletedGamesForm" class="operation-form rpgui-container framed-golden">
                    <h3>🗑️👀 Juegos Eliminados</h3>
                    <div class="table-wrapper rpgui-container framed">
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Nombre</th>
                                    <th>Fecha</th>
                                    <th>Horas Vistas</th>
                                    <th>Pico Espectadores</th>
                                    <th>Pico Canales</th>
                                    <th>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${deletedGames.map(game => `
                                    <tr>
                                        <td>${game.id}</td>
                                        <td>${game.game}</td>
                                        <td>${game.date}</td>
                                        <td>${parseInt(game.hours_watched).toLocaleString()}</td>
                                        <td>${parseInt(game.peak_viewers).toLocaleString()}</td>
                                        <td>${parseInt(game.peak_channels).toLocaleString()}</td>
                                        <td>
                                            <button class="rpgui-button" onclick="recoverGame(${game.id})">
                                                <span>♻️ Recuperar</span>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            const formsContainer = document.querySelector('.forms-container');
            formsContainer.insertAdjacentHTML('beforeend', tableHTML);
            document.getElementById('deletedGamesForm').style.display = 'block';
        } else {
            alert('Error al cargar los juegos eliminados');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al cargar los juegos eliminados');
    }
}

// Function to recover a game from the deleted games list
async function recoverGame(gameId) {
    if (confirm(`¿Estás seguro de que deseas recuperar el juego con ID ${gameId}?`)) {
        try {
            const response = await fetch(`/api/games/recover/${gameId}`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('¡Juego recuperado correctamente!');
                location.reload();
            } else {
                const error = await response.json();
                alert('Error al recuperar el juego: ' + error.detail);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error al recuperar el juego');
        }
    }
}

// Add the restore form to the list of forms to hide
document.addEventListener('DOMContentLoaded', function() {
    // Check if hideAllForms function exists
    if (typeof hideAllForms === 'function') {
        // Store the original hideAllForms function
        const originalHideAllForms = hideAllForms;
        
        // Override the hideAllForms function to include the restoreForm
        window.hideAllForms = function() {
            // Call the original function
            originalHideAllForms();
            
            // Hide the restoreForm if it exists
            const restoreForm = document.getElementById('restoreForm');
            if (restoreForm) {
                restoreForm.style.display = 'none';
            }
        };
    }
});