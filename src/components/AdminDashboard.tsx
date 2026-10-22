import React, { useMemo, useState } from 'react';
import {
  Activity, AlertCircle, ArrowDownToLine, ArrowLeft, ArrowRight, BadgeCheck, BookOpen,
  Check, CheckCheck, ChevronDown, CircleHelp, Clock3, Eye, FileSearch, Filter, Flag,
  GraduationCap, LayoutDashboard, LifeBuoy, ListFilter, Menu, MessageSquareWarning,
  MoreHorizontal, Search, Settings, Shield, ShieldCheck, Sparkles, UserRound, Users,
  X
} from 'lucide-react';

interface AdminDashboardProps {
  onOpenLearnerView: () => void;
}

type AdminSection = 'overview' | 'moderation' | 'users' | 'authors' | 'complaints' | 'library' | 'settings';
type QueueStatus = 'Chờ duyệt' | 'Đang xử lý' | 'Đã duyệt';
type QueueItem = {
  id: number;
  title: string;
  category: 'Truyện chương' | 'Bản dịch' | 'Bài dịch cộng đồng' | 'Đề xuất học liệu';
  author: string;
  submitted: string;
  hsk: string;
  status: QueueStatus;
  image?: string;
};

const initialQueue: QueueItem[] = [
  { id: 1, title: 'Đấu La Đại Lục IV – Ngoại truyện: Học viện Sử Lai Khắc', category: 'Truyện chương', author: '@Tieuw_2k', submitted: '15 phút trước', hsk: 'HSK 3', status: 'Chờ duyệt', image: '/assets/imagetest/Image_7_135114e0.png' },
  { id: 2, title: 'Bản dịch: “Trăng ẩm thực Thần Ma Khách Điếm”', category: 'Bản dịch', author: '@BaoBao', submitted: '1 giờ trước', hsk: 'HSK 2', status: 'Chờ duyệt', image: '/assets/imagetest/Image_5_a0f946e7.jpeg' },
  { id: 3, title: 'Mẹo nhớ 50 từ HSK 4 qua truyện kiếm hiệp Kim Dung', category: 'Đề xuất học liệu', author: '@LaoSu_Minh', submitted: '2 giờ trước', hsk: 'HSK 4', status: 'Đang xử lý' },
  { id: 4, title: 'Chia sẻ ngữ pháp 把字句 qua hội thoại', category: 'Bài dịch cộng đồng', author: '@hanzi_daily', submitted: '3 giờ trước', hsk: 'HSK 3', status: 'Chờ duyệt' },
  { id: 5, title: 'Nhật Ký Tiểu Hồ Ly – Chương 8', category: 'Truyện chương', author: '@MiuMiu', submitted: 'Hôm qua', hsk: 'HSK 2', status: 'Đã duyệt', image: '/assets/imagetest/Image_3_49817239.jpeg' },
  { id: 6, title: 'Bản dịch: Thành phố trên mây', category: 'Bản dịch', author: '@YueYue', submitted: 'Hôm qua', hsk: 'HSK 5', status: 'Chờ duyệt', image: '/assets/imagetest/Image_10_7407c4c1.jpeg' }
];

const sections: { id: AdminSection; label: string; icon: React.ElementType; group: 'main' | 'learner' }[] = [
  { id: 'overview', label: 'Tổng quan', icon: LayoutDashboard, group: 'main' },
  { id: 'moderation', label: 'Duyệt bài công khai', icon: CheckCheck, group: 'main' },
  { id: 'users', label: 'Quản lý người dùng', icon: Users, group: 'main' },
  { id: 'authors', label: 'Duyệt tác giả', icon: ShieldCheck, group: 'main' },
  { id: 'complaints', label: 'CSKH & Khiếu nại', icon: LifeBuoy, group: 'main' },
  { id: 'library', label: 'Kho truyện Manhua', icon: BookOpen, group: 'main' },
  { id: 'settings', label: 'Cài đặt hệ thống', icon: Settings, group: 'main' }
];

const statusClass: Record<QueueStatus, string> = {
  'Chờ duyệt': 'bg-rose-100 text-rose-700',
  'Đang xử lý': 'bg-blue-100 text-blue-700',
  'Đã duyệt': 'bg-emerald-100 text-emerald-700'
};

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onOpenLearnerView }) => {
  const [activeSection, setActiveSection] = useState<AdminSection>('overview');
  const [queue, setQueue] = useState<QueueItem[]>(initialQueue);
  const [queueFilter, setQueueFilter] = useState<'Tất cả' | 'Chờ duyệt' | 'Đang xử lý' | 'Đã duyệt'>('Tất cả');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState('Mới nhất trước');
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<QueueItem | null>(null);
  const [notice, setNotice] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeQuickTab, setActiveQuickTab] = useState<AdminSection>('moderation');
  const [userFilter, setUserFilter] = useState<'Tất cả' | 'Đang hoạt động' | 'Bị cảnh báo'>('Tất cả');
  const [systemSettings, setSystemSettings] = useState([true, true, true, false]);

  const filteredQueue = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase('vi');
    const result = queue.filter(item => {
      const matchStatus = queueFilter === 'Tất cả' || item.status === queueFilter;
      const matchQuery = !query || `${item.title} ${item.author} ${item.category} ${item.hsk}`.toLocaleLowerCase('vi').includes(query);
      const matchSection = activeSection !== 'authors' || item.category === 'Truyện chương';
      return matchStatus && matchQuery && matchSection;
    });
    return sortOrder === 'Cũ nhất trước' ? [...result].reverse() : result;
  }, [activeSection, queue, queueFilter, searchQuery, sortOrder]);

  const visibleItems = filteredQueue.slice((page - 1) * 3, page * 3);
  const totalPages = Math.max(1, Math.ceil(filteredQueue.length / 3));

  const notify = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(''), 3200);
  };

  const setItemStatus = (id: number, status: QueueStatus) => {
    setQueue(current => current.map(item => item.id === id ? { ...item, status } : item));
    if (selectedItem?.id === id) setSelectedItem(current => current ? { ...current, status } : current);
    notify(status === 'Đã duyệt' ? 'Đã duyệt nội dung thành công.' : 'Đã chuyển nội dung sang hàng chờ xử lý.');
  };

  const changeSection = (section: AdminSection) => {
    setActiveSection(section);
    setPage(1);
    setSidebarOpen(false);
    if (section === 'moderation' || section === 'authors') setActiveQuickTab(section);
  };

  const title = sections.find(item => item.id === activeSection)?.label ?? 'Tổng quan';
  const queueCount = queue.filter(item => item.status === 'Chờ duyệt').length;

  const renderQueue = (compact = false) => (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 border-b border-slate-100">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {(['Tất cả', 'Chờ duyệt', 'Đang xử lý', 'Đã duyệt'] as const).map(filter => (
            <button key={filter} onClick={() => { setQueueFilter(filter); setPage(1); }} className={`px-3 py-1.5 rounded-full text-[11px] font-semibold whitespace-nowrap transition ${queueFilter === filter ? 'bg-pink-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              {filter}{filter === 'Tất cả' ? ` (${queue.length})` : filter === 'Chờ duyệt' ? ` (${queueCount})` : ''}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-[11px] text-slate-500 whitespace-nowrap">
          Sắp xếp:
          <select value={sortOrder} onChange={event => setSortOrder(event.target.value)} className="rounded-full bg-blue-50 px-3 py-1.5 text-slate-700 outline-none">
            <option>Mới nhất trước</option><option>Cũ nhất trước</option>
          </select>
        </label>
      </div>
      <div className="divide-y divide-slate-100">
        {visibleItems.length ? visibleItems.map(item => (
          <article key={item.id} className="grid grid-cols-[76px_minmax(0,1fr)] sm:grid-cols-[96px_minmax(0,1fr)_auto] gap-3 p-3 sm:p-4 hover:bg-slate-50/70">
            <div className="h-[82px] w-[76px] sm:w-[96px] rounded-lg overflow-hidden bg-blue-50 flex items-center justify-center">
              {item.image ? <img src={item.image} alt="Ảnh bìa nội dung" className="h-full w-full object-cover" /> : <div className="text-center text-blue-700"><GraduationCap size={22} className="mx-auto"/><span className="text-[10px] font-bold">{item.hsk} · Tài liệu</span></div>}
            </div>
            <div className="min-w-0 flex flex-col justify-center gap-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[9px] text-slate-400">{item.category}</span>
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${statusClass[item.status]}`}>{item.status}</span>
              </div>
              <h3 className="text-xs sm:text-sm font-bold text-slate-800 line-clamp-2">{item.title}</h3>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-500">
                <span className="inline-flex items-center gap-1"><UserRound size={11}/>{item.author}</span>
                <span className="inline-flex items-center gap-1"><Clock3 size={11}/>{item.submitted}</span>
                <span className="inline-flex items-center gap-1"><GraduationCap size={11}/>{item.hsk}</span>
              </div>
            </div>
            <div className={`${compact ? 'col-span-2 sm:col-span-1' : 'col-span-2 sm:col-span-1'} flex sm:flex-col justify-end sm:justify-center items-center gap-1.5`}>
              <button onClick={() => setSelectedItem(item)} className="px-2.5 py-1.5 rounded-full bg-blue-100 text-blue-800 text-[10px] font-bold inline-flex items-center gap-1 hover:bg-blue-200"><Eye size={12}/>Xem{!compact && ' & Soạn OCR'}</button>
              {item.status !== 'Đã duyệt' && <button onClick={() => setItemStatus(item.id, 'Đã duyệt')} className="px-2.5 py-1.5 rounded-full bg-pink-500 text-white text-[10px] font-bold inline-flex items-center gap-1 hover:bg-pink-600"><Check size={12}/>Phê duyệt ngay</button>}
              {item.status === 'Đã duyệt' && <span className="px-2.5 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold inline-flex items-center gap-1"><BadgeCheck size={12}/>Đã xuất bản</span>}
            </div>
          </article>
        )) : <div className="py-12 text-center text-sm text-slate-500">Không tìm thấy nội dung phù hợp.</div>}
      </div>
      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-[11px] text-slate-500">
        <span>Hiển thị {filteredQueue.length ? (page - 1) * 3 + 1 : 0}–{Math.min(page * 3, filteredQueue.length)} trong {filteredQueue.length} nội dung</span>
        <div className="flex items-center gap-1">
          <button aria-label="Trang trước" disabled={page <= 1} onClick={() => setPage(value => Math.max(1, value - 1))} className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center disabled:opacity-40"><ArrowLeft size={13}/></button>
          {Array.from({ length: totalPages }, (_, index) => index + 1).map(number => <button key={number} onClick={() => setPage(number)} className={`w-7 h-7 rounded-full text-[10px] font-bold ${page === number ? 'bg-pink-500 text-white' : 'hover:bg-slate-100'}`}>{number}</button>)}
          <button aria-label="Trang sau" disabled={page >= totalPages} onClick={() => setPage(value => Math.min(totalPages, value + 1))} className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center disabled:opacity-40"><ArrowRight size={13}/></button>
        </div>
      </div>
    </>
  );

  const renderUsers = () => {
    const users = [
      { name: 'Nguyễn Minh Anh', email: 'minhanh@example.com', role: 'Học viên', status: 'Đang hoạt động', level: 'HSK 4' },
      { name: 'Trần Bảo Ngọc', email: 'baongoc@example.com', role: 'Tác giả', status: 'Đang hoạt động', level: 'HSK 5' },
      { name: 'Lê Hoàng Nam', email: 'hoangnam@example.com', role: 'Học viên', status: 'Bị cảnh báo', level: 'HSK 2' },
      { name: 'Phạm Thu Hà', email: 'thuha@example.com', role: 'Học viên', status: 'Đang hoạt động', level: 'HSK 3' }
    ].filter(user => (userFilter === 'Tất cả' || user.status === userFilter) && `${user.name} ${user.email}`.toLowerCase().includes(searchQuery.toLowerCase()));
    return <div className="rounded-2xl border border-slate-100 bg-white overflow-hidden"><div className="flex gap-2 p-4 border-b border-slate-100">{(['Tất cả', 'Đang hoạt động', 'Bị cảnh báo'] as const).map(value => <button key={value} onClick={() => setUserFilter(value)} className={`px-3 py-1.5 rounded-full text-[11px] font-semibold ${userFilter === value ? 'bg-pink-500 text-white' : 'bg-slate-100 text-slate-600'}`}>{value}</button>)}</div><div className="divide-y divide-slate-100">{users.map(user => <div key={user.email} className="flex items-center justify-between gap-3 p-4"><div className="min-w-0"><div className="text-sm font-bold text-slate-800">{user.name}</div><div className="text-xs text-slate-500">{user.email} · {user.role} · {user.level}</div></div><button onClick={() => notify(`Đã mở hồ sơ ${user.name}.`)} className="px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 text-xs font-bold">Xem hồ sơ</button></div>)}</div>{users.length === 0 && <div className="p-8 text-center text-sm text-slate-500">Không có người dùng phù hợp.</div>}</div>;
  };

  return (
    <div className="min-h-screen bg-[#f7f8fd] text-slate-800 font-['Inter']">
      <header className="h-[62px] bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <button className="lg:hidden p-2 rounded-lg hover:bg-slate-100" onClick={() => setSidebarOpen(open => !open)} aria-label="Mở menu"><Menu size={19}/></button>
          <div className="w-9 h-9 rounded-xl bg-pink-100 text-pink-600 flex items-center justify-center"><Sparkles size={19}/></div>
          <div className="leading-tight"><div className="text-sm font-extrabold text-slate-900">Yinghua Admin</div><div className="text-[10px] text-slate-500">樱花 · 管理中心</div></div>
        </div>
        <div className="hidden md:flex items-center gap-2">
          <div className="relative"><Search size={14} className="absolute left-3 top-2.5 text-slate-400"/><input value={searchQuery} onChange={event => { setSearchQuery(event.target.value); setPage(1); }} placeholder="Tìm truyện, từ vựng, tài khoản" className="w-56 rounded-full bg-slate-100 py-2 pl-9 pr-3 text-[10px] outline-none focus:ring-2 focus:ring-pink-200" /></div>
          <span className="px-2.5 py-1.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-semibold inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500"/>Kiểm duyệt viên: Đang hoạt động</span>
          <button onClick={onOpenLearnerView} className="px-3 py-1.5 rounded-full bg-pink-100 text-pink-700 text-[10px] font-bold">Xem giao diện Học viên</button>
        </div>
        <div className="flex items-center gap-2"><button onClick={() => notify('Bạn đã xem tất cả thông báo mới.')} className="relative w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center"><AlertCircle size={16}/><span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-pink-500"/></button><div className="hidden sm:block text-right leading-tight"><div className="text-[11px] font-bold">Admin Yinghua</div><div className="text-[9px] text-slate-500">Quản trị viên cấp cao</div></div><div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-pink-100 flex items-center justify-center text-xs font-extrabold text-[#a43073]">A</div></div>
      </header>

      <div className="flex min-h-[calc(100vh-62px)]">
        <aside className={`${sidebarOpen ? 'block' : 'hidden'} lg:block fixed lg:sticky top-[62px] left-0 z-20 w-[230px] h-[calc(100vh-62px)] overflow-y-auto bg-white border-r border-slate-200 p-3`}>
          <p className="px-2 py-3 text-[9px] font-bold tracking-wider text-slate-400">ĐIỀU HƯỚNG CHÍNH</p>
          <nav className="flex flex-col gap-1">{sections.filter(section => section.group === 'main').map(({ id, label, icon: Icon }) => <button key={id} onClick={() => changeSection(id)} className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[11px] font-semibold ${activeSection === id ? 'bg-pink-500 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}><Icon size={15}/>{label}{id === 'complaints' && <span className="ml-auto rounded-full bg-rose-100 px-1.5 py-0.5 text-[9px] text-rose-700">9+</span>}</button>)}</nav>
          <p className="px-2 pt-6 pb-2 text-[9px] font-bold tracking-wider text-slate-400">GIAO DIỆN HỌC VIÊN</p>
          <button onClick={onOpenLearnerView} className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[11px] font-semibold text-slate-600 hover:bg-pink-50"><GraduationCap size={15}/>Mở trang học viên</button>
          <div className="mt-8 rounded-xl bg-blue-50 p-3"><div className="flex justify-between text-[9px] font-semibold"><span>Máy chủ hệ thống</span><span className="text-emerald-600">Ổn định</span></div><div className="mt-2 h-1 rounded-full bg-blue-200"><div className="h-full w-[92%] rounded-full bg-blue-600"/></div><div className="mt-1 text-[9px] text-slate-500">HSK 1–6 · Dữ liệu v2.4.0</div></div>
        </aside>

        <main className="min-w-0 flex-1 p-4 md:p-6 lg:p-7">
          <div className="mx-auto max-w-[1300px]">
            <div className="mb-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4 rounded-3xl bg-gradient-to-r from-white via-white to-pink-50 p-5 md:p-6 shadow-sm border border-slate-100">
              <div><div className="mb-1 inline-flex items-center gap-1 rounded-full bg-pink-100 px-2.5 py-1 text-[9px] font-bold text-pink-700"><Sparkles size={11}/>Phiên bản Yinghua Admin 2.4</div><h1 className="text-2xl md:text-[28px] font-extrabold tracking-tight text-slate-900">{activeSection === 'overview' ? 'Trung Tâm Quản trị Yinghua' : title}</h1><p className="mt-1 max-w-2xl text-xs text-slate-500">Giám sát phê duyệt bản thảo manhua, thẩm định tác giả và bảo vệ cộng đồng học tiếng Trung.</p></div>
              <div className="flex flex-wrap gap-2"><button onClick={() => { changeSection('moderation'); setQueueFilter('Chờ duyệt'); }} className="inline-flex items-center gap-1.5 rounded-full bg-sky-700 px-3.5 py-2 text-[10px] font-bold text-white hover:bg-sky-800"><ShieldCheck size={13}/>Duyệt nhanh theo AI</button><button onClick={() => notify('Đã tạo báo cáo kiểm duyệt mẫu.')} className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3.5 py-2 text-[10px] font-bold text-blue-800 hover:bg-blue-200"><ArrowDownToLine size={13}/>Xuất báo cáo vi phạm</button></div>
            </div>

            {activeSection === 'overview' && <>
              <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
                <StatCard title="Chờ duyệt công khai" value={`${queueCount + 12}`} suffix="nội dung" note="5 cần gấp" detail="Cập nhật 4 phút trước" color="pink" icon={<CheckCheck size={16}/>}/>
                <StatCard title="Tổng người dùng" value="24,850" suffix="học viên" note="+12% tuần này" detail="12 bị cảnh báo" color="blue" icon={<Users size={16}/>}/>
                <StatCard title="Đơn duyệt tác giả" value="7" suffix="hồ sơ mới" note="4 HSK 5+" detail="3 dịch giả HSK 6" color="amber" icon={<Shield size={16}/>}/>
                <StatCard title="Tỷ lệ chuẩn OCR" value="96.4%" suffix="tự động" note="" detail="≈ 0.88 giây" color="rose" icon={<Activity size={16}/>} progress={96.4}/>
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-4 gap-3 mb-5">
                <div className="rounded-2xl border border-pink-100 bg-white p-4 xl:col-span-1"><div className="flex items-center justify-between text-[10px] font-bold text-pink-700"><span>CSKH & Khiếu nại</span><MessageSquareWarning size={15}/></div><div className="mt-2 text-2xl font-extrabold text-rose-600">14 <span className="text-xs font-semibold text-slate-500">cần xử lý</span></div><div className="mt-1 text-[9px] text-slate-500">6 vi phạm dịch/OCR · 6 VIP · 3 nội dung</div></div>
                <div className="xl:col-span-3 rounded-2xl bg-white border border-slate-100 p-2 flex flex-wrap items-center justify-around gap-1">{([
                  { id: 'moderation', label: 'Duyệt bài công khai', count: queueCount, icon: CheckCheck },
                  { id: 'users', label: 'Quản lý người dùng', count: '24.8k', icon: Users },
                  { id: 'authors', label: 'Duyệt tác giả truyện', count: '7 mới', icon: ShieldCheck },
                  { id: 'complaints', label: 'Trung tâm CSKH & Khiếu nại', count: '14 mới', icon: LifeBuoy }
                ] as const).map(({ id, label, count, icon: Icon }) => <button key={id} onClick={() => changeSection(id)} className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-3 text-center text-[10px] font-semibold transition ${activeQuickTab === id ? 'bg-blue-50 text-[#a43073]' : 'text-slate-600 hover:bg-slate-50'}`}><Icon size={14}/><span>{label}<span className="ml-1 rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] text-blue-700">{count}</span></span></button>)}</div>
              </div>
              <Panel title="Hàng chờ kiểm duyệt" action={<button onClick={() => changeSection('moderation')} className="text-[10px] font-bold text-pink-600">Xem tất cả →</button>}>{renderQueue(true)}</Panel>
            </>}

            {activeSection === 'moderation' && <Panel title="Duyệt bài công khai" action={<button onClick={() => notify('Đã tải danh sách mới nhất.')} className="text-xs text-blue-700 inline-flex gap-1 items-center"><ListFilter size={13}/>Làm mới</button>}>{renderQueue()}</Panel>}
            {activeSection === 'authors' && <Panel title="Hồ sơ tác giả cần thẩm định">{renderQueue(true)}</Panel>}
            {activeSection === 'users' && <Panel title="Quản lý người dùng" action={<button onClick={() => notify('Đã xuất danh sách người dùng mẫu.')} className="text-xs text-blue-700 inline-flex gap-1"><ArrowDownToLine size={13}/>Xuất danh sách</button>}>{renderUsers()}</Panel>}
            {activeSection === 'complaints' && <Panel title="CSKH & Khiếu nại" action={<button onClick={() => notify('Đã lọc các yêu cầu mới.')} className="text-xs text-blue-700 inline-flex gap-1"><Filter size={13}/>Chỉ yêu cầu mới</button>}><div className="divide-y divide-slate-100">{['Báo cáo bản dịch sai nội dung', 'Không thể khôi phục chuỗi ngày học', 'Yêu cầu hỗ trợ tài khoản VIP'].map((item, index) => <div key={item} className="flex items-center justify-between gap-4 p-4"><div><div className="text-sm font-bold">{item}</div><div className="text-xs text-slate-500 mt-1">#{2408 + index} · {index + 1} giờ trước · Ưu tiên {index === 0 ? 'cao' : 'thường'}</div></div><button onClick={() => notify(`Đã nhận xử lý yêu cầu #${2408 + index}.`)} className="rounded-full bg-pink-100 px-3 py-1.5 text-[10px] font-bold text-pink-700">Nhận xử lý</button></div>)}</div></Panel>}
            {activeSection === 'library' && <Panel title="Kho truyện Manhua" action={<button onClick={() => notify('Đã mở biểu mẫu thêm truyện.')} className="rounded-full bg-pink-500 px-3 py-1.5 text-[10px] font-bold text-white">+ Thêm truyện</button>}><div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3 p-4">{initialQueue.filter(item => item.image).map(item => <div key={item.id} className="flex gap-3 rounded-xl border border-slate-100 p-3"><img src={item.image} alt="Bìa truyện" className="h-20 w-14 rounded-lg object-cover"/><div className="min-w-0"><div className="text-xs font-bold line-clamp-2">{item.title}</div><div className="mt-2 text-[10px] text-slate-500">{item.hsk} · {item.category}</div><button onClick={() => setSelectedItem(item)} className="mt-2 text-[10px] font-bold text-blue-700">Quản lý nội dung</button></div></div>)}</div></Panel>}
            {activeSection === 'settings' && <Panel title="Cài đặt hệ thống"><div className="grid sm:grid-cols-2 gap-3 p-4">{[['Chế độ kiểm duyệt AI', 'Tự động phân loại nội dung vi phạm'], ['OCR Real-time', 'Nhận diện chữ Hán và Pinyin'], ['Thông báo quản trị', 'Nhận cảnh báo khiếu nại mới'], ['Chế độ bảo trì', 'Tạm ẩn một số tính năng học viên']].map(([label, description], index) => <div key={label} className="flex items-center justify-between rounded-xl border border-slate-100 p-4"><div><div className="text-xs font-bold">{label}</div><div className="mt-1 text-[10px] text-slate-500">{description}</div></div><button role="switch" aria-checked={systemSettings[index]} onClick={() => { setSystemSettings(settings => settings.map((enabled, settingIndex) => settingIndex === index ? !enabled : enabled)); notify(`${label} đã được cập nhật.`); }} className={`relative h-5 w-9 rounded-full ${systemSettings[index] ? 'bg-blue-600' : 'bg-slate-300'}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${systemSettings[index] ? 'left-[18px]' : 'left-0.5'}`}/></button></div>)}</div></Panel>}
          </div>
        </main>
      </div>

      {notice && <div className="fixed bottom-5 right-5 z-50 rounded-xl bg-slate-900 px-4 py-3 text-xs font-semibold text-white shadow-lg">{notice}</div>}

      {selectedItem && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" onClick={() => setSelectedItem(null)}><section className="w-full max-w-lg rounded-2xl bg-white shadow-2xl" onClick={event => event.stopPropagation()}><div className="flex items-center justify-between border-b border-slate-100 p-4"><div><div className="text-[10px] font-bold uppercase text-pink-600">Xem nội dung · {selectedItem.category}</div><h2 className="mt-1 text-base font-bold">{selectedItem.title}</h2></div><button onClick={() => setSelectedItem(null)} aria-label="Đóng" className="rounded-full p-2 hover:bg-slate-100"><X size={17}/></button></div><div className="p-4"><div className="rounded-xl bg-blue-50 p-4 text-xs leading-relaxed text-slate-600"><div className="font-bold text-slate-800">Bản xem trước / OCR</div><p className="mt-2">识别文本：欢迎来到樱花中文学习平台。<br/>Pinyin: Huānyíng láidào Yīnghuā Zhōngwén xuéxí píngtái.<br/>Bản dịch: Chào mừng bạn đến với nền tảng học tiếng Trung Yinghua.</p></div><div className="mt-4 flex justify-end gap-2"><button onClick={() => setItemStatus(selectedItem.id, 'Đang xử lý')} className="rounded-full bg-blue-100 px-4 py-2 text-xs font-bold text-blue-800">Chuyển xử lý</button><button onClick={() => setItemStatus(selectedItem.id, 'Đã duyệt')} className="rounded-full bg-pink-500 px-4 py-2 text-xs font-bold text-white">Phê duyệt</button></div></div></section></div>}
    </div>
  );
};

const Panel: React.FC<{ title: string; action?: React.ReactNode; children: React.ReactNode }> = ({ title, action, children }) => <section className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm"><div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3"><h2 className="text-sm font-extrabold text-slate-800">{title}</h2>{action}</div>{children}</section>;

const StatCard: React.FC<{ title: string; value: string; suffix: string; note: string; detail: string; color: string; icon: React.ReactNode; progress?: number }> = ({ title, value, suffix, note, detail, color, icon, progress }) => {
  const palette: Record<string, string> = { pink: 'bg-pink-100 text-pink-700', blue: 'bg-blue-100 text-blue-700', amber: 'bg-amber-100 text-amber-700', rose: 'bg-rose-100 text-rose-700' };
  return <article className="rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm"><div className="flex items-center justify-between gap-2"><span className="text-[10px] font-semibold text-slate-500">{title}</span><span className={`flex h-7 w-7 items-center justify-center rounded-full ${palette[color]}`}>{icon}</span></div><div className="mt-2 flex items-baseline gap-1.5"><span className="text-2xl font-extrabold tracking-tight text-slate-900">{value}</span><span className="text-[9px] text-slate-500">{suffix}</span></div>{progress !== undefined ? <div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-full rounded-full bg-pink-600" style={{ width: `${progress}%` }}/></div> : null}<div className="mt-2 flex flex-wrap items-center gap-1.5">{note && <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${palette[color]}`}>{note}</span>}<span className="text-[9px] text-slate-500">{detail}</span></div></article>;
};
