import AppBar from './AppBar'
import Sidebar from './Sidebar'
import ToastContainer from './ToastContainer'

export default function Layout({ children }) {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <AppBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main
          className="flex-1 overflow-y-auto bg-page-bg dark:bg-gray-950"
          style={{ padding: '30px 38px' }}
        >
          {children}
        </main>
      </div>
      <ToastContainer />
    </div>
  )
}
