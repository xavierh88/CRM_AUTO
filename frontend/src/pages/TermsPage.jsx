import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function TermsPage() {
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
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Términos y Condiciones</h1>
          <p className="text-slate-500 mb-8">Última actualización: Enero 2026</p>

          <div className="prose prose-slate max-w-none">
            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">1. Aceptación de Términos</h2>
            <p className="text-slate-600 mb-4">
              Al acceder y utilizar los servicios de CARPLUS AUTOSALE ("Nosotros", "Nuestro", "la Empresa"), 
              usted acepta estar sujeto a estos Términos y Condiciones. Si no está de acuerdo con alguna 
              parte de estos términos, no podrá acceder al servicio.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">2. Descripción del Servicio</h2>
            <p className="text-slate-600 mb-4">
              CARPLUS AUTOSALE es un servicio de intermediación (brokerage) de vehículos que ayuda a 
              conectar compradores con opciones de financiamiento para la adquisición de automóviles. 
              Nuestros servicios incluyen:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li>Evaluación de pre-calificación para financiamiento</li>
              <li>Búsqueda de opciones de vehículos</li>
              <li>Coordinación con instituciones financieras</li>
              <li>Programación de citas y seguimiento</li>
              <li>Comunicaciones por SMS y correo electrónico</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">3. Consentimiento para Comunicaciones SMS</h2>
            <p className="text-slate-600 mb-4">
              Al proporcionar su número de teléfono y aceptar estos términos, usted consiente recibir 
              mensajes de texto (SMS) de CARPLUS AUTOSALE relacionados con:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li>Confirmaciones de citas</li>
              <li>Recordatorios de citas programadas</li>
              <li>Actualizaciones sobre su proceso de financiamiento</li>
              <li>Información sobre documentos requeridos</li>
              <li>Notificaciones importantes del servicio</li>
            </ul>
            <p className="text-slate-600 mb-4">
              <strong>Frecuencia de mensajes:</strong> Puede recibir hasta 5 mensajes por semana dependiendo 
              de la etapa de su proceso.
            </p>
            <p className="text-slate-600 mb-4">
              <strong>Cargos:</strong> Se pueden aplicar tarifas de mensajes y datos según su plan de telefonía móvil.
            </p>
            <p className="text-slate-600 mb-4">
              <strong>Cancelar suscripción:</strong> Puede cancelar los mensajes SMS en cualquier momento 
              respondiendo STOP a cualquier mensaje. Recibirá una confirmación de cancelación.
            </p>
            <p className="text-slate-600 mb-4">
              <strong>Ayuda:</strong> Responda HELP para obtener información de contacto y asistencia.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">4. Información del Usuario</h2>
            <p className="text-slate-600 mb-4">
              Usted se compromete a proporcionar información precisa, actual y completa durante el proceso 
              de registro y pre-calificación. Esto incluye pero no se limita a:
            </p>
            <ul className="list-disc pl-6 text-slate-600 mb-4">
              <li>Información de identificación personal</li>
              <li>Información de empleo e ingresos</li>
              <li>Información de residencia</li>
              <li>Documentos de identificación válidos</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">5. Privacidad y Protección de Datos</h2>
            <p className="text-slate-600 mb-4">
              Su privacidad es importante para nosotros. El uso de su información personal está regido por 
              nuestra <a href="/privacy" className="text-blue-600 hover:underline">Política de Privacidad</a>, 
              que forma parte integral de estos Términos y Condiciones.
            </p>
            <p className="text-slate-600 mb-4">
              <strong>No compartimos ni vendemos su información personal a terceros</strong> para fines de 
              marketing no relacionados con nuestros servicios.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">6. Limitación de Responsabilidad</h2>
            <p className="text-slate-600 mb-4">
              CARPLUS AUTOSALE actúa como intermediario y no garantiza la aprobación de financiamiento. 
              Las decisiones de crédito son tomadas por las instituciones financieras correspondientes 
              basándose en sus propios criterios de evaluación.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">7. Modificaciones</h2>
            <p className="text-slate-600 mb-4">
              Nos reservamos el derecho de modificar estos términos en cualquier momento. Los cambios 
              entrarán en vigor inmediatamente después de su publicación en este sitio web.
            </p>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">8. Contacto</h2>
            <p className="text-slate-600 mb-4">
              Si tiene preguntas sobre estos Términos y Condiciones, puede contactarnos:
            </p>
            <ul className="list-none text-slate-600 mb-4">
              <li><strong>CARPLUS AUTOSALE</strong></li>
              <li>7444 Florence Ave, Downey, CA 90240</li>
              <li>Teléfono: (213) 462-9914</li>
              <li>Email: info@carplusautosalesgroup.com</li>
            </ul>

            <h2 className="text-xl font-semibold text-slate-800 mt-6 mb-4">9. Ley Aplicable</h2>
            <p className="text-slate-600 mb-4">
              Estos Términos y Condiciones se regirán e interpretarán de acuerdo con las leyes del 
              Estado de California, Estados Unidos.
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
