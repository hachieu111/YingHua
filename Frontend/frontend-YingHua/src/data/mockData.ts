import { ComicSeries, ComicPage, VocabularyItem, LeaderboardUser, FlashcardDeck } from '../types';

export const COMIC_PAGES: ComicPage[] = [
  {
    id: 'page_4',
    pageNumber: 4,
    title: 'Trang 04 - Lam Hiên Vũ tâm trạng rất tốt',
    imageSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAOydlzp-Y5DeGe1Y9AT-UivLYt5SIcK908IpjHPW3wvyDUPdHjSlqNaQFNhspUtNu7LyhJ1GpygAaDjOOlhaVBs6w6zvQzth0A9aq6uT_J5Qw5CxjraALsLeeGm2a9r3CV0OAbTGGw3HiL91n_nclRLe7E828EhWXYJcz-OEw7NVQBGHtv-tIAqS8gdxF5ipw7llonfGEqQPxiDYrYVx1VHra4hhZ7a9b7ct3bPukVKdpXJ8VHHfL_uWilOD7Dhgim7w',
    bubbles: [
      {
        id: 'bubble_1',
        top: '14.5%',
        right: '5.5%',
        width: '36%',
        height: '10.5%',
        type: 'dialogue',
        hanzi: '期末考试即将面临。',
        pinyin: 'qī mò kǎo shì jí jiāng miàn lín',
        vietnamese: 'Kỳ thi cuối kỳ sắp diễn ra rồi.',
        locationLabel: 'Góc trên phải',
        vocabChips: [
          { word: '期末', meaning: 'cuối kỳ' },
          { word: '考试', meaning: 'kỳ thi' },
          { word: '即将', meaning: 'sắp sửa' },
          { word: '面临', meaning: 'đối mặt / diễn ra' }
        ]
      },
      {
        id: 'bubble_2',
        top: '37.5%',
        left: '18.2%',
        width: '26%',
        height: '14%',
        type: 'narration',
        hanzi: '今天蓝轩宇心情很好，',
        pinyin: 'jīn tiān lán xuān yǔ xīn qíng hěn hǎo',
        vietnamese: 'Hôm nay Lam Hiên Vũ tâm trạng rất tốt,',
        locationLabel: 'Giữa bên trái',
        vocabChips: [
          { word: '今天', meaning: 'hôm nay' },
          { word: '蓝轩宇', meaning: 'Lam Hiên Vũ' },
          { word: '心情', meaning: 'tâm trạng' },
          { word: '很好', meaning: 'rất tốt' }
        ]
      },
      {
        id: 'bubble_3',
        top: '55%',
        right: '23.5%',
        width: '33%',
        height: '21.5%',
        type: 'grammar',
        hanzi: '因为爸爸答应他，如果考试成绩好。',
        pinyin: 'yīn wèi bà ba dā ying tā, rú guǒ kǎo shì chéng jì hǎo',
        vietnamese: 'Bởi vì bố đã hứa với cậu ấy, nếu kết quả thi tốt,',
        locationLabel: 'Dưới phải (trên)',
        vocabChips: [
          { word: '因为', meaning: 'bởi vì' },
          { word: '答应', meaning: 'hứa hẹn / đồng ý' },
          { word: '如果', meaning: 'nếu' },
          { word: '成绩', meaning: 'thành tích / kết quả' }
        ]
      },
      {
        id: 'bubble_4',
        top: '76%',
        right: '14.8%',
        width: '33%',
        height: '20.8%',
        type: 'dialogue',
        hanzi: '就带他坐星际飞船，去天斗星玩。',
        pinyin: 'jiù dài tā zuò xīng jì fēi chuán, qù tiān dǒu xīng wán',
        vietnamese: 'Thì sẽ đưa cậu đi tàu vũ trụ đến sao Thiên Đấu chơi.',
        locationLabel: 'Dưới cùng phải',
        vocabChips: [
          { word: '就', meaning: 'thì' },
          { word: '星际飞船', meaning: 'tàu vũ trụ / phi thuyền' },
          { word: '天斗星', meaning: 'sao Thiên Đấu' },
          { word: '玩', meaning: 'chơi' }
        ]
      }
    ],
    vocabulary: [
      { hanzi: '期末考试', pinyin: 'qī mò kǎo shì', vietnamese: 'Kỳ thi cuối kỳ' },
      { hanzi: '面临', pinyin: 'miàn lín', vietnamese: 'Sắp diễn ra / đối mặt' },
      { hanzi: '答应', pinyin: 'dā ying', vietnamese: 'Hứa hẹn, đồng ý' },
      { hanzi: '星际飞船', pinyin: 'xīng jì fēi chuán', vietnamese: 'Tàu vũ trụ / phi thuyền liên sao' }
    ],
    grammarSpotlight: {
      pattern: '如果……就…… (Rúguǒ... jiù...)',
      description: 'Biểu thị điều kiện giả thiết: "Nếu [vế A điều kiện] thì [vế B kết quả]".',
      exampleHanzi: '如果考试成绩好，就带他去天斗星玩。',
      examplePinyin: 'Rúguǒ kǎoshì chéngjì hǎo, jiù dài tā qù Tiāndǒuxīng wán.',
      exampleVietnamese: '"Nếu kết quả thi tốt thì sẽ đưa cậu ấy đến sao Thiên Đấu chơi."'
    }
  },
  {
    id: 'page_5',
    pageNumber: 5,
    title: 'Trang 05 - Bắt mẹ ôm hôn',
    imageSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAQi1JKkscrvPktQvd0-HY3cQPXBBNQtuONR-CyBC_E9Bl0QHo_Feohi9A0bOZ8gAWGtq4VXoZY8ENwE7PrinQLdqk8OY6DehWTIc1YtNwTA49IDCgHyTtv1aZ78wgrpAy47D9bGgUiUGAjOfByQFNvAwPInv73Ei-GjDGoSwLcQr1OxgzMZmHu6vTO9IhDG7MCHnMMeICJ322wLxqT1Hc37TJLs-MaW9r8AhKMjHZHgOj8uLcs6PDGyDc6Lwue3IT5Ew',
    bubbles: [
      {
        id: 'bubble_5_1',
        top: '12%',
        left: '10%',
        width: '38%',
        height: '18%',
        type: 'dialogue',
        hanzi: '妈妈，你来陪我好不好？',
        pinyin: 'mā ma, nǐ lái péi wǒ hǎo bù hǎo?',
        vietnamese: 'Mẹ ơi, mẹ đến cùng chơi với con được không?',
        locationLabel: 'Góc trên trái',
        vocabChips: [
          { word: '妈妈', meaning: 'mẹ' },
          { word: '陪', meaning: 'đồng hành / ở bên' },
          { word: '好不好', meaning: 'được không' }
        ]
      },
      {
        id: 'bubble_5_2',
        top: '10%',
        right: '12%',
        width: '32%',
        height: '22%',
        type: 'dialogue',
        hanzi: '抓到我，我就让你亲一下。',
        pinyin: 'zhuā dào wǒ, wǒ jiù ràng nǐ qīn yī xià.',
        vietnamese: 'Bắt được con thì con mới cho mẹ hôn một cái nè.',
        locationLabel: 'Góc trên phải',
        vocabChips: [
          { word: '抓到', meaning: 'bắt được' },
          { word: '让', meaning: 'cho phép / để' },
          { word: '亲一下', meaning: 'hôn một cái' }
        ]
      },
      {
        id: 'bubble_5_3',
        top: '60%',
        left: '20%',
        width: '30%',
        height: '16%',
        type: 'dialogue',
        hanzi: '抓你？干嘛！',
        pinyin: 'zhuā nǐ? gàn ma!',
        vietnamese: 'Bắt con á? Làm trò gì vậy!',
        locationLabel: 'Bên dưới trái',
        vocabChips: [
          { word: '抓', meaning: 'bắt' },
          { word: '干嘛', meaning: 'làm gì / sao thế' }
        ]
      }
    ],
    vocabulary: [
      { hanzi: '陪', pinyin: 'péi', vietnamese: 'Ở bên, đồng hành, bồi tiếp' },
      { hanzi: '抓到', pinyin: 'zhuā dào', vietnamese: 'Bắt được, tóm lấy' },
      { hanzi: '亲', pinyin: 'qīn', vietnamese: 'Hôn, thân mật' },
      { hanzi: '干嘛', pinyin: 'gàn ma', vietnamese: 'Làm cái gì, sao vậy (khẩu ngữ)' }
    ],
    grammarSpotlight: {
      pattern: '……好不好？(... hǎo bù hǎo?)',
      description: 'Dùng ở cuối câu để thăm dò ý kiến hoặc đề xuất một cách thân thiện, ngọt ngào.',
      exampleHanzi: '明天我们一起去，好不好？',
      examplePinyin: 'Míngtiān wǒmen yīqǐ qù, hǎo bù hǎo?',
      exampleVietnamese: '"Ngày mai chúng mình cùng đi nhé, được không nào?"'
    }
  },
  {
    id: 'page_6',
    pageNumber: 6,
    title: 'Trang 06 - Bữa ăn ngon lành',
    imageSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAV5EIXD1MStadtH5j20dMt5t_npUus3Hcgx86oRMMjJ7zfhe6qJfSrqY9WYqFCCat2jG2x7dfyjZdOrVL-e4UrurZRPY0nHuczNTm26TEIF-MCwwuhtRRzQsxE_M76KiyVcOVC-ppktHSGcRidMdTiFwdqtJ4_yi_ox_LtIz2cneg2Je5aVo8m9uLUDi_an98rwO2209UokA-8vfPFaWhnDvvpRpfvmnxFLnEreWnabIH0eyMOyBqh1quqmZt-vgTRxw',
    bubbles: [
      {
        id: 'bubble_6_1',
        top: '18%',
        left: '20%',
        width: '35%',
        height: '24%',
        type: 'dialogue',
        hanzi: '哇，好好吃哦！',
        pinyin: 'wā, hǎo hǎo chī ó!',
        vietnamese: 'Oa, ngon miệng quá đi mất!',
        locationLabel: 'Khung thoại giữa',
        vocabChips: [
          { word: '哇', meaning: 'oa (cảm thán)' },
          { word: '好好吃', meaning: 'rất ngon miệng' },
          { word: '哦', meaning: 'trợ từ cảm thán' }
        ]
      },
      {
        id: 'bubble_6_2',
        top: '55%',
        left: '12%',
        width: '32%',
        height: '20%',
        type: 'dialogue',
        hanzi: '这是什么呀？',
        pinyin: 'zhè shì shén me ya?',
        vietnamese: 'Đây là món gì vậy ạ?',
        locationLabel: 'Góc dưới trái',
        vocabChips: [
          { word: '这是', meaning: 'đây là' },
          { word: '什么', meaning: 'cái gì' }
        ]
      }
    ],
    vocabulary: [
      { hanzi: '好吃', pinyin: 'hǎo chī', vietnamese: 'Ngon miệng, ngon' },
      { hanzi: '什么', pinyin: 'shén me', vietnamese: 'Cái gì (đại từ nghi vấn)' },
      { hanzi: '美味', pinyin: 'měi wèi', vietnamese: 'Mỹ vị, cao lương mỹ vị' }
    ]
  },
  {
    id: 'page_7',
    pageNumber: 7,
    title: 'Trang 07 - Lớp học kiểm tra',
    imageSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDO1RyPOuemYSGBa0zrTDK76wS7raJkEq8HNovi841AOkZlUDEV-1aYr2UF08Zk1U99oPxZvI5EDafN4HjS5gMqpqY8iRGArFkuTETIJOHHrFL8FNU4gE1y7XeCdMpo4DC5lIDAd6cIakKoH-33zCGFawgS1F-3Iv6MLXBwnqzj6OYD7HDFFJUFvWw9byjJ5tOLkAvd3GEJskCHZND90RZphVtU3ugzsEZTTZDXfmQHIWZ8qrN7WVAVYnbip1CSXDovvA',
    bubbles: [
      {
        id: 'bubble_7_1',
        top: '12%',
        left: '18%',
        width: '32%',
        height: '18%',
        type: 'dialogue',
        hanzi: '黄启帆，上！',
        pinyin: 'huáng qǐ fān, shàng!',
        vietnamese: 'Hoàng Khải Phàm, lên đi!',
        locationLabel: 'Góc trên trái',
        vocabChips: [
          { word: '上', meaning: 'lên / tiến lên' }
        ]
      },
      {
        id: 'bubble_7_2',
        top: '15%',
        right: '15%',
        width: '26%',
        height: '18%',
        type: 'dialogue',
        hanzi: '嗯！',
        pinyin: 'èn!',
        vietnamese: 'Dạ!',
        locationLabel: 'Góc trên phải',
        vocabChips: [
          { word: '嗯', meaning: 'ừ / vâng' }
        ]
      },
      {
        id: 'bubble_7_3',
        top: '65%',
        right: '20%',
        width: '34%',
        height: '22%',
        type: 'dialogue',
        hanzi: '轩宇你第一个上吧。',
        pinyin: 'xuān yǔ nǐ dì yī gè shàng ba.',
        vietnamese: 'Hiên Vũ, em là người đầu tiên lên nhé.',
        locationLabel: 'Dưới phải',
        vocabChips: [
          { word: '第一个', meaning: 'người đầu tiên' },
          { word: '上吧', meaning: 'lên đi nhé' }
        ]
      }
    ],
    vocabulary: [
      { hanzi: '第一个', pinyin: 'dì yī gè', vietnamese: 'Người đầu tiên, thứ nhất' },
      { hanzi: '上', pinyin: 'shàng', vietnamese: 'Lên (bục), xuất trận' },
      { hanzi: '准备', pinyin: 'zhǔn bèi', vietnamese: 'Chuẩn bị' }
    ]
  }
];

export const ALL_COMICS: ComicSeries[] = [
  {
    id: 'douluo4',
    title: 'Đấu La Đại Lục IV: Chung Cực Đấu La',
    chineseTitle: '斗罗大陆IV 终极斗罗',
    author: 'Đường Gia Tam Thiếu',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAjjt5VzTWVMhZzha4IkASeE0WwigZ2iTjjL2GZcyci48MRs-ViCkNz059NVv2xf7VfYLrU34az0M1fmvZCxu2iubW5iHx0zpOwGNTS8jqRchu50eK18nXmazip9vkL5I0sm7gvgUgDMQp7gzo9xZ60cm5atuykxb9gr7LHW6g8TOEFdXDhKR6Gjvso8qYavDUmq0nwT0OmSw5atWNXH7PtQCQnujc7ooV2rVgXtrwvCA6tto8uMo1V',
    hskLevel: 'HSK 4',
    genre: 'Huyền Huyễn • Tu Tiên',
    description: 'Cùng theo chân Lam Hiên Vũ khám phá thế giới hồn sư vị lai. Học hơn 650 từ vựng trình độ HSK 4 qua hội thoại trường học, gia đình và phiêu lưu thám hiểm sống động.',
    progressPercent: 22,
    currentPage: 4,
    totalPages: 18,
    totalChapters: 45,
    currentChapterTitle: 'Chương 12: Long Thần Huyết Mạch',
    savedVocabCount: 35,
    rating: 4.9,
    isFavorite: true,
    status: 'reading',
    pages: COMIC_PAGES
  },
  {
    id: 'quanzhigaoshou',
    title: 'Toàn Chức Cao Thủ',
    chineseTitle: '全职高手',
    author: 'Hồ Điệp Lam',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAJOKIclDvw2i21x1Od-DPEWN33DITSebWaQjrlKeDKmUumUbXslOtT6_bi2brl9FGPLk0aXT9hoJ7Vynu7VxFc0TDa1iDFqCTd6nONCoouhJsLSGM3Cum8sYWMsrGFkYH2OKcJBMLGr_WJ9YRM0ttmYLPLXm6xWspvVoaNreRssap8zI-Tjbi8sNOIAlsmoQ0ubn72K0tDzw0lj6z4v6mZ3ufcDXPUwMwpVsZNyU2y_27t7jCMxmiq',
    hskLevel: 'HSK 3+',
    genre: 'Võng Du • Thể Thao Điện Tử',
    description: 'Khẩu ngữ hiện đại, từ lóng mạng và phản xạ giao tiếp tốc độ cao. Theo chân cao thủ Diệp Tu tái xuất giang hồ Vinh Quang.',
    progressPercent: 68,
    currentPage: 15,
    totalPages: 22,
    totalChapters: 52,
    currentChapterTitle: 'Chương 35: Tiệm Net Hưng Hân',
    savedVocabCount: 62,
    rating: 4.8,
    isFavorite: true,
    status: 'reading'
  },
  {
    id: 'modaozushi',
    title: 'Ma Đạo Tổ Sư (Tiền Truyện)',
    chineseTitle: '魔道祖师',
    author: 'Mặc Hương Đồng Khứu',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAeZz5zMbFqhb2VyranIoyp23y9WizCzr3bI1lxfVVOz3r8HYxS5QBDOJBHPVKjuZ8hdgyRqxM4mYu5_kiijZBQr8-q3l01N-CtZ57JFrJn4vGlmAjd68vDFm5wWdGOaHkvDQCF7kpG5g3U6toe9GzO93SxKLWwFV1SVEnfhxpTLb8Rq9xuv7FeiPE9cjAFwDyPJa1fIZEqS6SkGzHx3VyX7W0r56rNgHO5eS4sYwZLczEnXwXoOTmJ',
    hskLevel: 'HSK 5',
    genre: 'Cổ Phong • Tiên Hiệp',
    description: 'Văn phong cổ trang uyển chuyển, trau dồi hệ thống thành ngữ 4 chữ (成语) kinh điển và từ xưng hô tôn kính thời xưa.',
    progressPercent: 8,
    currentPage: 2,
    totalPages: 25,
    totalChapters: 60,
    currentChapterTitle: 'Chương 03: Vân Thâm Bất Tri Xứ',
    savedVocabCount: 42,
    rating: 4.95,
    isFavorite: true,
    status: 'reading'
  },
  {
    id: 'amthuctinhcau',
    title: 'Ẩm Thực Tinh Cầu',
    chineseTitle: '星际美食家',
    author: 'Lam Hiên',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBHBgjH3-B4PFCw3Gpkbi17LDCGnvGScI5_cfVneCueK8TAje8e-OsxBv_UjJYDxqAty8YRlBOp-YVw5BIHPLUZLaz5jmE73ZmC3JRe6S_hiI1vYnaxFUl3MzhdQTEkiG_LM1zQWWCB2nJ6mlffoIH6TVmbuRkK_uKxI4386bbfDn-qP7xvHHmu-ot7RGsHpmG6uFNvK3T8JEw3XEIyb6Y16rN2NZWYX9Vo0J18gof14Ti0HfaprnAjUftyHOekd9rSYw',
    hskLevel: 'HSK 2',
    genre: 'Ẩm thực & Hài hước',
    description: 'Chàng trai trẻ xuyên không cùng bí kíp làm món thịt kho tàu Thượng Hải siêu ngon, học tên nguyên liệu và gia vị hằng ngày.',
    progressPercent: 22,
    currentPage: 4,
    totalPages: 18,
    totalChapters: 24,
    currentChapterTitle: 'Chương 4: Món Thịt Kho Tàu Kỳ Diệu',
    savedVocabCount: 35,
    rating: 4.7,
    status: 'reading'
  },
  {
    id: 'caphemuaha',
    title: 'Cà Phê Mùa Hạ',
    chineseTitle: '夏日咖啡日记',
    author: 'Tiểu Vũ',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBfwmV7VcZJ3AQbPZ3bVummWcQ6a8SDkC543uMjpKiPac5ifTX90voGQzmUT1WSebeDdriaj3gnxJ6ULg5RX8lK4afhTWG4WN8n68BzBb5y0FjxUxCiu988Ti-qKO9FWVrYqT8BVDhjJtkRJd1QNj_BImaQiqFTQBbAPhFb6f1BYL16k_2uI_wz0FQAxVb22Ua8QiVjohK1CpuOmaEkhjKWvgvFk03RhGdWK07StKwJkSYuKv-QZz43',
    hskLevel: 'HSK 1',
    genre: 'Đời thường & Giao tiếp',
    description: 'Cách gọi đồ uống, chào hỏi thường nhật và số đếm đơn giản qua nét vẽ tươi sáng, phù hợp người mới bắt đầu.',
    progressPercent: 100,
    currentPage: 18,
    totalPages: 18,
    totalChapters: 12,
    currentChapterTitle: 'Chương 12: Tách Cà Phê Cuối Mùa',
    savedVocabCount: 42,
    rating: 4.9,
    status: 'completed'
  },
  {
    id: 'khanhdunien',
    title: 'Khánh Dư Niên: Tiền Truyện',
    chineseTitle: '庆余年',
    author: 'Miêu Nị',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBC8He5QwcQZnxEJRIiGltLMzUV5wjlHyhkjir7Tit2YKD6HD7q5nvTXZOwTQFbmsUnk3CJ9-wrrbiJYBNEibE8KXAakuDX6KNgoBVE-JyPRbEbwCZQzFMKuDFpUSuSFSsaCt0y3RC1kmmIQhOB6BOQvOyK39tvkTOCKC4R71wPrjvZ3zis8jvHEdCWZxcr7RAAM83LfkD3FrHyzcHyVfbciv5V1AzjzBzoSSF4ts2X23MbYzL7heMr',
    hskLevel: 'HSK 4',
    genre: 'Cung Đình • Quyền Mưu',
    description: 'Tập hợp hệ thống từ vựng mưu lược, thương trường và văn hóa lịch sử phong phú bậc nhất.',
    progressPercent: 30,
    currentPage: 12,
    totalPages: 42,
    totalChapters: 36,
    currentChapterTitle: 'Chương 14: Đạm Châu Hội Ngộ',
    savedVocabCount: 54,
    rating: 4.85,
    status: 'saved'
  },
  {
    id: 'vungtromkhongthegiau',
    title: 'Vụng Trộm Không Thể Giấu',
    chineseTitle: '偷偷藏不住',
    author: 'Trúc Dĩ',
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBKsf9x9AzFCTqMlsEuRtRz5vsQkCGdh2-FbNu5TsOSPBtfimoC0PagKmajIQwcVeUY-fnoTGlO19rOALfdps7FWwxmN3_h4uLJuKbHEiQc5hPgM6H5RB5g-Qpor7EXak91PxYJqdGA8K0Wu6e_lT89_5JvaapuV3ZfqarNejgW3dbD828AWMM6EJu7yAqwMEc3BTCQsEVe2CWM2zf7pkI0r4uwrSlpboz1RighgljNqtkDSGy4Yszm',
    hskLevel: 'HSK 4',
    genre: 'Thanh Xuân • Ngôn Tình',
    description: 'Văn phong giao tiếp tự nhiên của giới trẻ Trung Quốc, biểu đạt cảm xúc tinh tế, hơn 120 câu giao tiếp đời sống.',
    progressPercent: 45,
    currentPage: 18,
    totalPages: 40,
    totalChapters: 45,
    currentChapterTitle: 'Chương 18: Kẹo Hồ Lô Bên Đường',
    savedVocabCount: 48,
    rating: 4.95,
    status: 'saved'
  }
];

export const VOCABULARY_LIST: VocabularyItem[] = [
  {
    id: 'v1',
    hanzi: '答应',
    pinyin: 'dāying',
    sinoVietnamese: 'Đáp Ứng',
    vietnamese: 'Đồng ý, nhận lời, đáp lời, hứa hẹn',
    hskLevel: 4,
    comicSource: 'Ma Đạo Tổ Sư - Chap 28',
    status: 'mastered',
    isStarred: true,
    exampleSentence: {
      hanzi: '你既然已经答应了他，就绝不能反悔。',
      pinyin: 'Nǐ jìrán yǐjīng dāying le tā, jiù jué bùnéng fǎnhuǐ.',
      vietnamese: 'Ngươi đã nhận lời hắn rồi, tuyệt đối không được nuốt lời.'
    }
  },
  {
    id: 'v2',
    hanzi: '彷徨',
    pinyin: 'pánghuáng',
    sinoVietnamese: 'Bàng Hoàng',
    vietnamese: 'Do dự, đi đi lại lại, bế tắc không lối thoát',
    hskLevel: 6,
    comicSource: 'Khánh Dư Niên - Chap 14',
    status: 'reviewing',
    isStarred: false,
    exampleSentence: {
      hanzi: '面对未知的未来，他心中不免有些彷徨。',
      pinyin: 'Miànduì wèizhī de wèilái, tā xīnzhōng bùmiǎn yǒuxiē pánghuáng.',
      vietnamese: 'Đối mặt với tương lai mịt mờ, trong lòng chàng không khỏi có chút bàng hoàng do dự.'
    }
  },
  {
    id: 'v3',
    hanzi: '执念',
    pinyin: 'zhíniàn',
    sinoVietnamese: 'Chấp Niệm',
    vietnamese: 'Ý nghĩ cố chấp, không thể buông bỏ',
    hskLevel: 5,
    comicSource: 'Đấu La Đại Lục IV - Chap 102',
    status: 'needs_review',
    isStarred: true,
    exampleSentence: {
      hanzi: '成全别人，也是放下自己的执念。',
      pinyin: 'Chéngquán biérén, yě shì fàngxià zìjǐ de zhíniàn.',
      vietnamese: 'Tác thành cho người khác cũng chính là buông bỏ chấp niệm của bản thân.'
    }
  },
  {
    id: 'v4',
    hanzi: '坦白',
    pinyin: 'tǎnbái',
    sinoVietnamese: 'Thản Bạch',
    vietnamese: 'Thành thật, thẳng thắn thú nhận',
    hskLevel: 4,
    comicSource: 'Toàn Chức Cao Thủ - Chap 50',
    status: 'mastered',
    isStarred: false,
    exampleSentence: {
      hanzi: '与其隐瞒，不如坦白承认错误。',
      pinyin: 'Yǔqí yǐnmán, bùrú tǎnbái chéngrèn cuòwù.',
      vietnamese: 'Thay vì giấu giếm, chẳng thà thẳng thắn nhận lỗi.'
    }
  },
  {
    id: 'v5',
    hanzi: '奇遇',
    pinyin: 'qíyù',
    sinoVietnamese: 'Kỳ Ngộ',
    vietnamese: 'Cuộc gặp gỡ kỳ lạ, cơ duyên bất ngờ',
    hskLevel: 5,
    comicSource: 'Ma Đạo Tổ Sư - Chap 12',
    status: 'reviewing',
    isStarred: true,
    exampleSentence: {
      hanzi: '少年在此处有了一番非凡的奇遇。',
      pinyin: 'Shàonián zài cǐ chù yǒule yī fān fēifán de qíyù.',
      vietnamese: 'Thiếu niên ở nơi này đã có một phen kỳ ngộ phi phàm.'
    }
  },
  {
    id: 'v6',
    hanzi: '面临',
    pinyin: 'miànlín',
    sinoVietnamese: 'Diện Lâm',
    vietnamese: 'Sắp diễn ra, đối mặt với',
    hskLevel: 4,
    comicSource: 'Đấu La Đại Lục IV - Chap 12',
    status: 'mastered',
    isStarred: true,
    exampleSentence: {
      hanzi: '期末考试即将面临，大家都抓紧时间复习。',
      pinyin: 'Qīmò kǎoshì jíjiāng miànlín, dàjiā dōu zhuājǐn shíjiān fùxí.',
      vietnamese: 'Kỳ thi cuối kỳ sắp cận kề, mọi người đều tranh thủ ôn tập.'
    }
  },
  {
    id: 'v7',
    hanzi: '星际飞船',
    pinyin: 'xīngjì fēichuán',
    sinoVietnamese: 'Tinh Tế Phi Thuyền',
    vietnamese: 'Tàu vũ trụ, phi thuyền liên sao',
    hskLevel: 4,
    comicSource: 'Đấu La Đại Lục IV - Chap 12',
    status: 'reviewing',
    isStarred: false,
    exampleSentence: {
      hanzi: '星际飞船划过浩瀚的银河。',
      pinyin: 'Xīngjì fēichuán huàguò hàohàn de yínhé.',
      vietnamese: 'Tàu vũ trụ rạch ngang dải ngân hà bao la.'
    }
  }
];

export const FLASHCARD_DECKS: FlashcardDeck[] = [
  {
    id: 'deck_1',
    title: 'Ma Đạo Tổ Sư (魔道祖师)',
    comicName: 'Ma Đạo Tổ Sư',
    badge: 'Manhua Cổ Phong',
    badgeColor: 'bg-primary-fixed text-primary',
    vocabCount: 58,
    reviewedCount: 42,
    description: 'Chuyên các cụm từ xưng hô cổ trang, kiếm hiệp, tu tiên và khẩu ngữ truyền cảm.',
    keyWords: '血脉, 觉醒, 精神力'
  },
  {
    id: 'deck_2',
    title: 'Đấu La Đại Lục IV (斗罗大陆)',
    comicName: 'Đấu La Đại Lục IV',
    badge: 'Huyền Huyễn',
    badgeColor: 'bg-secondary-fixed text-secondary',
    vocabCount: 35,
    reviewedCount: 17,
    description: 'Từ vựng về hành động, chiến đấu kịch tính, biểu cảm cảm xúc nhân vật.',
    keyWords: '武魂, 魂环, 魂导器'
  },
  {
    id: 'deck_3',
    title: 'Khánh Dư Niên (庆余年)',
    comicName: 'Khánh Dư Niên',
    badge: 'Quyền Mưu Trí Tuệ',
    badgeColor: 'bg-amber-100 text-amber-900',
    vocabCount: 42,
    reviewedCount: 12,
    description: 'Từ ngữ chính trị cung đình, thương trường và châm ngôn đối nhân xử thế.',
    keyWords: '官场, 策略, 忠诚'
  },
  {
    id: 'deck_4',
    title: 'Từ Vựng Đánh Dấu Sao ⭐',
    comicName: 'Bộ sưu tập cá nhân',
    badge: 'Quan Trọng Nhất',
    badgeColor: 'bg-primary text-white',
    vocabCount: 64,
    reviewedCount: 64,
    description: 'Tất cả các từ bạn chủ động lưu lại khi đang đắm mình trong các tập truyện tranh.',
    keyWords: '64 Từ Ưu Tiên'
  }
];

export const LEADERBOARD_USERS: LeaderboardUser[] = [
  {
    rank: 1,
    name: 'Bạch Thiển',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDjUr4FMb4MgwcGmdyBYosbOItcdlvEkxu9VuOkv4yChU6EPBmWHSxMyaIG2w7JyQSlJ3zh4VkfCAHFuSSY-0bwHegxn1MY8EwBXQDq5YEuIMo6kduC811ATR-vUrWSRZiJDDw4Dv4kfEcji9H1h-Frrh68cI9XZpGjabLqD7QeFSRUy5m8nMQbUcYmyVvydukRzllNvxE0yWo2vXMWSiwKMCQRmHm73bSNJPX1IKlAOx5ut-6odYJ9',
    hskLevel: 'HSK 5',
    pagesRead: 98,
    exp: 3420,
    streakDays: 28,
    vocabCount: 365,
    tag: 'Đệ Nhất Học Giả 🌸'
  },
  {
    rank: 2,
    name: 'Tiểu Vũ Trụ',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA_uMPLrijjganO12yjzcqBT4iRom9EHHW5tkEKYy0s6bzONjjZJOsKMo1tHWZ8Mi_cej435rLx8tBS0eHe8LCMLexJUN5tPcGo1NTdFzzBTxXd91zyr0yJy6Da72aTL-lo0Szz_EN_4TtVoml8l2HoF628gmirX8rQ_7mEIpNRWkRQZ9pB6UXBT70FsGbmfLvFNCAM-h3ZCTUHpDJNDHRqG45SO6jydevpkFNc0CxToqjFs2LON3aY',
    hskLevel: 'HSK 4',
    pagesRead: 84,
    exp: 2890,
    streakDays: 14,
    vocabCount: 290
  },
  {
    rank: 3,
    name: 'Mạc Vấn',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBVjkBiWmwVafJMFy9b38FOH42tFaihJElRLi9nDAV5kkc2iezdzuP8nQD_WcpKsTydMuQn7_BGS5NPclc7mAdJJyAjVL3PVN0CQfH4wExm8ENDZuz7UW0VNFXP-dC-NzRpy-7pc9aq-C3NNor8-m5kSohpalM-Ea01ca-lKrmXCfBGC1iQjCcKw3fvo3hfAom1pRQq31RocIYeNSPlzBzO6CsCRH05YkdOae0ppcgrnQlYGso1XlIQ',
    hskLevel: 'HSK 4',
    pagesRead: 76,
    exp: 2650,
    streakDays: 11,
    vocabCount: 245
  },
  {
    rank: 4,
    name: 'Lạc Ly',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA9DFVyAwp3qs6bCCAS8H7_nzT-vbOYDPJDn1sNqw2e5llwn6Uto6fdyGaQKtiWpeJBD07ciJ_TsXHxC_7piD5Mb4fO5S3MIAIWQPQsagQhycr6kl0mfSytJWJ3I1ik8Bu9TPR-bvLR4y9YezoQpbtLX9ir-kDT0dKus1c04xqvISFIQWbYsZ-l5T0KOSCsSCNoPqxw5lOdQofxtc9g1tSnZlOZgE_5h1ddlLI2IfB1P52BGomg0e5T',
    hskLevel: 'HSK 4',
    pagesRead: 68,
    exp: 2410,
    streakDays: 22,
    vocabCount: 215,
    tag: 'Cần mẫn 📚'
  },
  {
    rank: 5,
    name: 'Tạ Du',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuABlqUt8ibmtbhlp1XLqeJdDtY9rV1YRz0Il9QIHnI3nxMaFOh6Mr2Uq8uVDIENKwdnk4rt__njwpG8Hx0dcLyBVv6mtuSIqaSGye0CQSvzi9eoFJGpTOoM41UdlO1QKCAqsJ_UQcUWQn3b8P90WEWIH3_kC46h_3vOr-70is1LgSNy_TJOoN8-T1z_5eJ8FVFQyWVCitlwaaGhClGlY68P0JGHxFucFFXSjZ1TPn9_mgLbk27WmgnH',
    hskLevel: 'HSK 4',
    pagesRead: 62,
    exp: 2280,
    streakDays: 9,
    vocabCount: 198,
    tag: 'Đột phá ⚡'
  },
  {
    rank: 6,
    name: 'Nhiếp Phong',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBg1vzc5qZmZB3ymS_JaUqaw8FwjbOI3MCZrkpGQ_QOT8dokIriRL9bfsU3sZ1Hv_YgIIcspooZLpJ0J9Vb00kebYaqYCgd3de7wARjh9rKv3iAJpU8xB9BSAJPg3LVIoKl_Du55A-lNanz84ACxQPuc3Tfvj3B0OU1uG1w5soPRmPitR8HGmGgGrCRqfZuXnfdOsw0lJkLO_JMH2-agfu1e3SNIp1l05h2QiN7IvhFg7GTlS5L64h5',
    hskLevel: 'HSK 3',
    pagesRead: 57,
    exp: 2140,
    streakDays: 15,
    vocabCount: 175
  },
  {
    rank: 7,
    name: 'Cố Tiêu',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCxWm_FKg_Wkkl59OawEaqn8OwSC1INIbjiLPOAPqhyjU2pDYNGvn_MM8DzQ0-QqCqtolcZIXozfKDBe5RfM_4_ElqJ3PzxTNvYxtiBO2kOEe60x2hKc4K_tswGInloRKoSIeoKzMa59_xRNSZhqZm3TDWtPRvTGYtLM21FDe-jmJol74AC2UnGAwfjCEtRhnTzdqx3p10YXE8s4tTJfxqmPDwBSvK-KJnyy-6DUmkPqF_JQRsX5QBN',
    hskLevel: 'HSK 3',
    pagesRead: 51,
    exp: 1990,
    streakDays: 8,
    vocabCount: 160,
    tag: 'Tốc độ 🚀'
  },
  {
    rank: 8,
    name: 'Hạ Mộng Dao',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAc2YA5-XfzjfsOJjRTw33bZSy8ZP3tiQKtz52bUKULT5_9Kbg56RPe4Z2KHZE7mL6BoRJ0Or1ZLlQxNcrvsxslxkxMvX4XIK_LhAT5NX5sW5MiFslZfOOnqSJd-3X2FtX2qWgIxkUyF2PJ4mobO0BvB5uPKbkk9A7IzgYrcqI1iiKQEF-msD02V89iFRcKnKa0Hp18ti4NnClP9ZqTrW3UETWhoErK0IX1tnrjUDayLfJAlgD_D2ad',
    hskLevel: 'HSK 4',
    pagesRead: 48,
    exp: 1870,
    streakDays: 12,
    vocabCount: 148
  },
  {
    rank: 9,
    name: 'Sở Hàn Vân',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDhfqQg1PF7kTc4w9QkHZJHcQyVT5VPWtnegxrLkqn_kfD8gxDUwSTqSi5WNT46A1bj7QbGaWdlDhbMrLZ9zvG4s9QwtWw-qt0Efd3isTWARWUGyBQg1CXBxxGVkZHk9quDlfDvkyL5FnNpDS1hofPkR0lPeFz7c3nNwqVdDKWpVQ6Zkzlmbb_jVETg1pFenLQfjf2Q8FRKlmOTrdBtntBoRlMWGYc8d3vx29xGzzA7I3wlWiNcl4x7',
    hskLevel: 'HSK 3',
    pagesRead: 44,
    exp: 1720,
    streakDays: 6,
    vocabCount: 130
  },
  {
    rank: 10,
    name: 'Đường Vũ Cách',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDJcEM3NLR-AviNBrJMKhEZ8qRGkbXyxYjUIuGQyypkI99y-z0fYTZTPQ7EiOrLikaF-ztPlHyJ2_VVI0XieAYBsfso880xUUsRUOxkD9ZUi5isB0imCITzh7-t4sjOg6LSPyuM6hSlsFl2Uuk-i3Jr4QLQRJXUf9GN8QPWdqjuE8QrWtyDcc9clr6ZcMBsZEg6hDgr8LyTOh-BLZ5-xq2pErMpKqytwgSGqmsPTs5BAFMIkBYqiBFK',
    hskLevel: 'HSK 2',
    pagesRead: 40,
    exp: 1610,
    streakDays: 18,
    vocabCount: 118,
    tag: 'Top 10 🌟'
  },
  {
    rank: 18,
    name: 'Lam Hiên Vũ',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDouZjBIU9lI8mNPf-eu9v9WtamqAGj2p9GPjLNQt-W3hkLMoboWClFeN1wnO4reJTt623UqgtV7sJWTBZNtrFULAAXa_41CVt1ROrHqL64Mt0hCpqhgY5UTLxSAkXf-fdF7PnB-_CsuutWeSJYspalRkRCCKxE8AkIKcYGrOLBFHbjBFp6Ljll9-mSx90EzZUcRzR8Cj7_VM-vjsotklPmMQYldFasjlGLovnzMABNqni9r2ipQklp',
    hskLevel: 'HSK 4',
    pagesRead: 32,
    exp: 1250,
    streakDays: 7,
    vocabCount: 486,
    isCurrentUser: true,
    tag: 'Bạn'
  }
];

export const CURRENT_USER = {
  name: 'Lam Hiên Vũ',
  chineseName: '轩宇',
  badge: 'Thành viên Hoa Anh Đào',
  hskLevel: 'Cấp độ HSK 4 - Độc Giả Chăm Chỉ',
  id: '#YH-8924',
  vipExpiry: '15/12/2025',
  joinDate: '12/03/2024',
  email: 'hienvu.manhua@yinghua.vn',
  avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDouZjBIU9lI8mNPf-eu9v9WtamqAGj2p9GPjLNQt-W3hkLMoboWClFeN1wnO4reJTt623UqgtV7sJWTBZNtrFULAAXa_41CVt1ROrHqL64Mt0hCpqhgY5UTLxSAkXf-fdF7PnB-_CsuutWeSJYspalRkRCCKxE8AkIKcYGrOLBFHbjBFp6Ljll9-mSx90EzZUcRzR8Cj7_VM-vjsotklPmMQYldFasjlGLovnzMABNqni9r2ipQklp',
  streak: 7,
  totalVocab: 486,
  pagesRead: 142,
  hoursLearned: 38.5,
  weeklyProgress: {
    current: 14,
    target: 20
  }
};
