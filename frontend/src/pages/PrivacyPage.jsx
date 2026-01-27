import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function PrivacyPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => navigate(-1)}
            className="text-slate-300 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
          <img 
            src="https://carplusautosalesgroup.com/img/carplus.png" 
            alt="CARPLUS" 
            className="h-8"
          />
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-xl p-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Política de Privacidad</h1>
          <p className="text-slate-500 mb-8">Última actualización: Enero 2026</p>

          <div className="prose prose-slate max-w-none">
            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">1. Introducción</h2>
            <p className="text-slate-600 mb-4">
              CARPLUS AUTOSALE ("Nosotros", "Nuestro", "la Empresa") se compromete a proteger la privacidad 
              de nuestros clientes y visitantes. Esta Política de Privacidad explica cómo recopilamos, 
              usamos, divulgamos y protegemos su información cuando utiliza nuestros servicios.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">2. Información que Recopilamos</h2>
            <p className="text-slate-600 mb-4">
              Recopilamos información que usted nos proporciona directamente, incluyendo:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li><strong>Información de identificación:</strong> Nombre completo, fecha de nacimiento, 
              número de identificación (licencia de conducir, pasaporte, etc.)</li>
              <li><strong>Información de contacto:</strong> Dirección, número de teléfono, correo electrónico</li>
              <li><strong>Información financiera:</strong> Información de empleo, ingresos, historial crediticio 
              (cuando sea necesario para el proceso de financiamiento)</li>
              <li><strong>Información de residencia:</strong> Dirección actual, tiempo en la residencia, 
              tipo de vivienda</li>
              <li><strong>Documentos:</strong> Copias de identificación, comprobantes de ingresos y residencia</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">3. Cómo Usamos su Información</h2>
            <p className="text-slate-600 mb-4">
              Utilizamos la información recopilada para:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li>Procesar su solicitud de pre-calificación</li>
              <li>Comunicarnos con usted sobre su proceso de compra</li>
              <li>Enviar recordatorios de citas por SMS y correo electrónico</li>
              <li>Coordinar con instituciones financieras para opciones de financiamiento</li>
              <li>Mejorar nuestros servicios</li>
              <li>Cumplir con obligaciones legales y regulatorias</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">4. Comunicaciones SMS</h2>
            <p className="text-slate-600 mb-4">
              Con su consentimiento, le enviaremos mensajes de texto (SMS) para:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li>Confirmar citas programadas</li>
              <li>Enviar recordatorios de citas</li>
              <li>Notificar actualizaciones importantes de su proceso</li>
              <li>Solicitar documentos necesarios</li>
            </ul>
            <p className="text-slate-600 mb-4">
              <strong>Puede cancelar los mensajes SMS en cualquier momento respondiendo STOP.</strong> 
              Se pueden aplicar tarifas de mensajes y datos según su operador móvil.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">5. Compartir Información</h2>
            <p className="text-slate-600 mb-4">
              <strong>No vendemos, alquilamos ni compartimos su información personal con terceros para 
              fines de marketing.</strong>
            </p>
            <p className="text-slate-600 mb-4">
              Podemos compartir su información únicamente con:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li><strong>Instituciones financieras:</strong> Para procesar solicitudes de financiamiento 
              (solo con su autorización expresa)</li>
              <li><strong>Proveedores de servicios:</strong> Que nos ayudan a operar nuestro negocio 
              (procesamiento de pagos, comunicaciones)</li>
              <li><strong>Autoridades legales:</strong> Cuando sea requerido por ley o proceso legal</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">6. Seguridad de Datos</h2>
            <p className="text-slate-600 mb-4">
              Implementamos medidas de seguridad técnicas y organizativas para proteger su información, 
              incluyendo:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li>Encriptación de datos sensibles</li>
              <li>Acceso restringido a información personal</li>
              <li>Servidores seguros con protección contra acceso no autorizado</li>
              <li>Capacitación regular del personal en protección de datos</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">7. Sus Derechos</h2>
            <p className="text-slate-600 mb-4">
              Usted tiene derecho a:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li><strong>Acceder:</strong> Solicitar una copia de su información personal</li>
              <li><strong>Corregir:</strong> Solicitar la corrección de información inexacta</li>
              <li><strong>Eliminar:</strong> Solicitar la eliminación de su información personal</li>
              <li><strong>Cancelar:</strong> Optar por no recibir comunicaciones de marketing</li>
              <li><strong>Portabilidad:</strong> Solicitar sus datos en formato electrónico</li>
            </ul>
            <p className="text-slate-600 mb-4">
              Para ejercer estos derechos, contáctenos usando la información proporcionada al final de 
              esta política.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">8. Retención de Datos</h2>
            <p className="text-slate-600 mb-4">
              Conservamos su información personal solo durante el tiempo necesario para cumplir con los 
              propósitos descritos en esta política, a menos que la ley requiera un período de retención 
              más largo.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">9. Privacidad de Menores</h2>
            <p className="text-slate-600 mb-4">
              Nuestros servicios no están dirigidos a personas menores de 18 años. No recopilamos 
              intencionalmente información de menores de edad.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">10. Cambios a esta Política</h2>
            <p className="text-slate-600 mb-4">
              Podemos actualizar esta Política de Privacidad periódicamente. Le notificaremos sobre 
              cambios significativos publicando la nueva política en nuestro sitio web.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">11. Contacto</h2>
            <p className="text-slate-600 mb-4">
              Si tiene preguntas sobre esta Política de Privacidad o desea ejercer sus derechos, 
              puede contactarnos:
            </p>
            <ul className="list-none text-slate-600 mb-4">
              <li><strong>CARPLUS AUTOSALE</strong></li>
              <li>7444 Florence Ave, Downey, CA 90240</li>
              <li>Teléfono: (213) 462-9914</li>
              <li>Email: privacy@carplusautosalesgroup.com</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">12. Información para Residentes de California</h2>
            <p className="text-slate-600 mb-4">
              Si usted es residente de California, tiene derechos adicionales bajo la Ley de Privacidad 
              del Consumidor de California (CCPA), incluyendo el derecho a saber qué información personal 
              recopilamos y cómo la usamos, y el derecho a solicitar la eliminación de su información.
            </p>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-200">
            <p className="text-sm text-slate-500 text-center">
              © 2026 CARPLUS AUTOSALE. Todos los derechos reservados.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
