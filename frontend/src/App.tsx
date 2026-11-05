import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { RequireRole, ToastProvider } from './components/ui'
import { AdminLayout } from './pages/admin/AdminLayout'
import { Appointments } from './pages/admin/Appointments'
import { DoctorEdit, DoctorsAdmin } from './pages/admin/Doctors'
import { Notifications } from './pages/admin/Notifications'
import { Patients } from './pages/admin/Patients'
import { Reports } from './pages/admin/Reports'
import { Settings } from './pages/admin/Settings'
import { Specializations } from './pages/admin/Specializations'
import { History } from './pages/doctor/History'
import { Schedule } from './pages/doctor/Schedule'
import { MyAppointments } from './pages/patient/MyAppointments'
import { Profile } from './pages/patient/Profile'
import { Login, Register } from './pages/public/Auth'
import { DoctorPage } from './pages/public/DoctorPage'
import { Doctors } from './pages/public/Doctors'
import { Home } from './pages/public/Home'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="doctors" element={<Doctors />} />
              <Route path="doctors/:id" element={<DoctorPage />} />
              <Route path="login" element={<Login />} />
              <Route path="register" element={<Register />} />

              <Route
                path="my"
                element={
                  <RequireRole role="patient">
                    <MyAppointments />
                  </RequireRole>
                }
              />
              <Route
                path="profile"
                element={
                  <RequireRole role="patient">
                    <Profile />
                  </RequireRole>
                }
              />

              <Route
                path="doctor"
                element={
                  <RequireRole role="doctor">
                    <Schedule />
                  </RequireRole>
                }
              />
              <Route
                path="doctor/history"
                element={
                  <RequireRole role="doctor">
                    <History />
                  </RequireRole>
                }
              />

              <Route
                path="admin"
                element={
                  <RequireRole role="admin">
                    <AdminLayout />
                  </RequireRole>
                }
              >
                <Route index element={<Reports />} />
                <Route path="appointments" element={<Appointments />} />
                <Route path="notifications" element={<Notifications />} />
                <Route path="doctors" element={<DoctorsAdmin />} />
                <Route path="doctors/new" element={<DoctorEdit />} />
                <Route path="doctors/:id" element={<DoctorEdit />} />
                <Route path="specializations" element={<Specializations />} />
                <Route path="patients" element={<Patients />} />
                <Route path="settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
