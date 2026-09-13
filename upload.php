<?php
// Clave de autenticación para la subida
$token_secreto = "MiClaveSegura2026";

// Validación de credenciales y archivo
if (!isset($_POST['token']) || $_POST['token'] !== $token_secreto || !isset($_FILES['pdf'])) {
    http_response_code(403);
    echo "Acceso no autorizado.";
    exit;
}

$nombre_fichero = basename($_FILES['pdf']['name']);
$extension = strtolower(pathinfo($nombre_fichero, PATHINFO_EXTENSION));

// Validación de tipo de archivo
if ($extension !== 'pdf') {
    http_response_code(400);
    echo "Solo se permiten archivos PDF.";
    exit;
}

// Ruta de destino en la misma carpeta del script
$destino = __DIR__ . '/' . $nombre_fichero;

if (move_uploaded_file($_FILES['pdf']['tmp_name'], $destino)) {
    http_response_code(200);
    echo "Fichero publicado correctamente.";
} else {
    http_response_code(500);
    echo "Error de permisos en el servidor al mover el archivo a: " . $destino;
}