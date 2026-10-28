var idAEliminar = null;
var csrfToken = null;

function abrirEliminar(boton) {
    idAEliminar = boton.dataset.id;
    csrfToken = boton.dataset.csrf;
    document.getElementById("modal-titulo").textContent = boton.dataset.titulo;
    document.getElementById("modal-motivo").value = "";
    document.getElementById("modal-eliminar").hidden = false;
}

function cerrarEliminar() {
    document.getElementById("modal-eliminar").hidden = true;
}

function confirmarEliminar() {
    var motivo = document.getElementById("modal-motivo").value.trim();
    if (!motivo) {
        alert("Por favor indica el motivo de la eliminación.");
        return;
    }
    var form = document.getElementById("form-eliminar");
    form.action = "/eliminar/" + idAEliminar;
    document.getElementById("input-motivo").value = motivo;
    document.getElementById("input-csrf").value = csrfToken;
    form.submit();
}

document.addEventListener("DOMContentLoaded", function () {
    var modal = document.getElementById("modal-eliminar");
    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target === this) {
                cerrarEliminar();
            }
        });
    }
});

