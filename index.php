<?php
// Carpeta donde se almacenan físicamente los PDF dentro del NAS
$pdf_dir = __DIR__ . '/';

$deca_id = isset($_GET['id']) ? preg_replace('/[^a-zA-Z0-9_-]/', '', $_GET['id']) : '';
$file_path = $pdf_dir . $deca_id . '.pdf';

if (empty($deca_id) || !file_exists($file_path)) {
    http_response_code(404);
    echo "Documento DeCA no encontrado.";
    exit;
}

// Control de expiración a los 7 días naturales (Apartado Tercero.5)
if ((time() - filemtime($file_path)) > (7 * 86400)) {
    http_response_code(410);
    echo "El enlace de descarga ha expirado conforme a la normativa.";
    exit;
}

// Descarga e inspección directa sin pasarelas (Apartado Tercero.3 y 4)
header('Content-Type: application/pdf');
header('Content-Disposition: inline; filename="DeCA_' . $deca_id . '.pdf"');
header('Content-Length: ' . filesize($file_path));
readfile($file_path);
exit;