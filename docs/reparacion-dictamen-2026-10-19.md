# Reparación del detalle de dictamen — 19/10/2026

Incidente: [run 39310957020](https://github.com/cepoes100b/CEPOES/actions/runs/39310957020), job 118260077423, rechazado por `2947-D-2026: dictamen detallado incompleto`.

Fuente del diagnóstico recibido: https://parlamentaria.legislatura.gob.ar/pages/expediente.aspx?id=142552. El 19/10 registra `Dictámen / UNICO DE COMISION`, con grilla vacía y movimientos hasta 24/9 `EN COMISION`, sin movimiento de dictamen. La comisión no puede obtenerse de ese evento ni atribuirse desde la ubicación previa.

`fallback_dictamenes` sólo emite detalles cuando dispone de fecha y comisión no vacías. Aplica la misma precondición a sus dos caminos (evento con movimiento y movimiento solo). Preserva las grillas existentes y la evidencia oficial original. La clasificación de hitos sigue usando tipos/subtipos oficiales y movimientos explícitos; el evento conserva `tuvo_dictamen`, `evidencia_dictamen` y la etapa histórica correspondiente aunque no haya detalle. El estado actual sigue dependiendo de movimientos. El validador permanece sin cambios.

Se trata de hacer cumplir el contrato existente de detalle, sin cambiar la metodología de clasificación, inferir una comisión ni suprimir el evento. Un fallo general de extracción continúa siendo rechazado por el control agregado del validador.

Pruebas reproducibles: `python -m unittest -v test_completar_ciclo_legislativo`; seis casos con regresión integrada contra el validador, grilla completa, evento y movimiento completos, movimiento completo aislado, campos incompletos y notas libres. El control negativo reintroduce el detalle nulo y debe ser rechazado. Se incorpora la suite al workflow canónico de validación legislativa. También: `python verificar_ciclo_legislativo.py`, compilación Python y `git diff --check`.

Alcance: generador, regresiones, validación CI y esta nota. Sin cambios a newsletter, editoriales, SUACI, secretos, suscriptores o permisos. La publicación requiere comprobar por separado el commit del productor y los archivos canónicos públicos; CI verde por sí solo no acredita actualización pública.
