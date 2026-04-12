/* ═══════════════════════════════════════════════════════
   CROPS DATA  —  22 crops matching the ML model exactly
   Names are Title-cased; lookup in recommend.js uses
   .toLowerCase() on both sides so backend lowercase
   labels like "pomegranate" resolve correctly.

   sowMonths    : Array of ideal sowing months [1–12].
                  Derived from the standard Indian agricultural calendar.
   isPerennial  : true = year-round / multi-year crop.
                  Season-check logic skips timing warnings for these.
═══════════════════════════════════════════════════════ */
const CROPS = [
  {name:'Rice',emoji:'🌾',season:'kharif',type:'cereal',bg:'#E8F5E9',
   sowMonths:[6,7], isPerennial:false,
   N:[60,100],P:[30,50],K:[30,60],pH:[5.5,7],T:[20,35],H:[60,95],R:[150,300],
   tip:'Rice thrives in flooded paddies. Ensure standing water during the vegetative stage.',
   altSeason:'Kharif',altSeasonIcon:'🌧️',altSeasonDesc:'Sown June–July, harvested October–November'},

  {name:'Wheat',emoji:'🌾',season:'rabi',type:'cereal',bg:'#FFF8E1',
   sowMonths:[11,12], isPerennial:false,
   N:[50,90],P:[30,60],K:[25,50],pH:[6,7.5],T:[10,25],H:[40,70],R:[50,100],
   tip:'Wheat requires cool temperatures during germination. Avoid waterlogging.',
   altSeason:'Rabi',altSeasonIcon:'❄️',altSeasonDesc:'Sown November–December, harvested April'},

  {name:'Maize',emoji:'🌽',season:'kharif',type:'cereal',bg:'#FFFDE7',
   sowMonths:[6,7], isPerennial:false,
   N:[60,120],P:[25,50],K:[30,70],pH:[5.8,7.5],T:[18,35],H:[50,75],R:[80,200],
   tip:'Maize is sensitive to waterlogging. Well-drained loamy soil is preferred.',
   altSeason:'Kharif',altSeasonIcon:'🌧️',altSeasonDesc:'Sown June–July, harvested September–October'},

  {name:'Chickpea',emoji:'🫘',season:'rabi',type:'pulse',bg:'#FBE9E7',
   sowMonths:[10,11], isPerennial:false,
   N:[15,40],P:[30,60],K:[20,40],pH:[6,8.5],T:[15,30],H:[30,60],R:[40,80],
   tip:'Chickpea fixes atmospheric nitrogen. Minimal N application needed.',
   altSeason:'Rabi',altSeasonIcon:'❄️',altSeasonDesc:'Sown October–November, harvested February–March'},

  {name:'Lentil',emoji:'🫘',season:'rabi',type:'pulse',bg:'#F3E5F5',
   sowMonths:[10,11,12], isPerennial:false,
   N:[10,30],P:[20,50],K:[20,40],pH:[6,7.5],T:[12,25],H:[30,55],R:[30,65],
   tip:'Lentils are drought-tolerant. Ideal for low-rainfall areas in winter.',
   altSeason:'Rabi',altSeasonIcon:'❄️',altSeasonDesc:'Sown October–December, harvested March–April'},

  {name:'Cotton',emoji:'🌸',season:'kharif',type:'fibre',bg:'#E3F2FD',
   sowMonths:[4,5,6], isPerennial:false,
   N:[60,120],P:[20,60],K:[30,60],pH:[5.8,8],T:[21,38],H:[50,80],R:[60,150],
   tip:'Cotton needs a frost-free period of 6–8 months. Deep black soil is ideal.',
   altSeason:'Kharif',altSeasonIcon:'🌧️',altSeasonDesc:'Sown April–June, harvested October–November'},

  {name:'Sugarcane',emoji:'🎋',season:'zaid',type:'cereal',bg:'#E8F5E9',
   sowMonths:[2,3], isPerennial:false,
   N:[80,140],P:[40,80],K:[60,100],pH:[6,8.5],T:[21,38],H:[70,95],R:[100,250],
   tip:'Sugarcane is a heavy feeder. Split fertilizer application ensures steady growth.',
   altSeason:'Zaid',altSeasonIcon:'☀️',altSeasonDesc:'Planted February–March, harvested after 10–18 months'},

  {name:'Mango',emoji:'🥭',season:'zaid',type:'fruit',bg:'#FFF3E0',
   sowMonths:[], isPerennial:true,
   N:[40,80],P:[20,40],K:[40,80],pH:[5.5,7.5],T:[24,38],H:[50,80],R:[75,150],
   tip:'Mango trees require a dry spell before flowering. Avoid excess nitrogen.',
   altSeason:'Zaid',altSeasonIcon:'☀️',altSeasonDesc:'Harvested April–July depending on variety'},

  {name:'Banana',emoji:'🍌',season:'zaid',type:'fruit',bg:'#FFFDE7',
   sowMonths:[], isPerennial:true,
   N:[80,140],P:[30,60],K:[100,200],pH:[6,7.5],T:[20,35],H:[70,90],R:[100,200],
   tip:'Banana is a potassium-intensive crop. Adequate K improves bunch weight significantly.',
   altSeason:'Zaid',altSeasonIcon:'☀️',altSeasonDesc:'Year-round; takes 9–12 months from planting'},

  {name:'Watermelon',emoji:'🍉',season:'zaid',type:'fruit',bg:'#FCE4EC',
   sowMonths:[2,3,4], isPerennial:false,
   N:[40,80],P:[20,50],K:[30,70],pH:[6,7],T:[25,38],H:[50,70],R:[40,80],
   tip:'Watermelon needs warm sandy soils and full sunlight for sweet fruit development.',
   altSeason:'Zaid',altSeasonIcon:'☀️',altSeasonDesc:'Sown February–April, harvested May–June'},

  {name:'Pigeonpea',emoji:'🫘',season:'kharif',type:'pulse',bg:'#F9FBE7',
   sowMonths:[6,7], isPerennial:false,
   N:[10,30],P:[25,50],K:[15,40],pH:[5.5,7.5],T:[18,35],H:[40,70],R:[60,150],
   tip:'Arhar/Tur is highly drought-tolerant. Deep taproot accesses subsoil moisture.',
   altSeason:'Kharif',altSeasonIcon:'🌧️',altSeasonDesc:'Sown June–July, harvested November–January'},

  {name:'Mustard',emoji:'🌻',season:'rabi',type:'oilseed',bg:'#FFFDE7',
   sowMonths:[10,11], isPerennial:false,
   N:[40,80],P:[15,40],K:[15,40],pH:[6,8],T:[10,25],H:[35,60],R:[25,75],
   tip:'Mustard is highly cold-tolerant and suitable for saline-alkaline soils.',
   altSeason:'Rabi',altSeasonIcon:'❄️',altSeasonDesc:'Sown October–November, harvested February–March'},

  {name:'Coffee',emoji:'☕',season:'zaid',type:'plantation',bg:'#EFEBE9',
   sowMonths:[], isPerennial:true,
   N:[80,120],P:[40,80],K:[40,80],pH:[6,6.8],T:[15,28],H:[60,90],R:[100,300],
   tip:'Coffee requires shade and well-drained acidic soil. Avoid temperatures above 30°C.',
   altSeason:'Perennial',altSeasonIcon:'🌿',altSeasonDesc:'Harvested October–February; takes 3–4 years to first yield'},

  {name:'Coconut',emoji:'🥥',season:'zaid',type:'plantation',bg:'#E0F7FA',
   sowMonths:[], isPerennial:true,
   N:[50,100],P:[20,60],K:[50,100],pH:[5.5,7.5],T:[25,38],H:[70,90],R:[100,200],
   tip:'Coconut thrives in coastal humid climates. Regular potassium application boosts nut yield.',
   altSeason:'Perennial',altSeasonIcon:'🌴',altSeasonDesc:'Year-round bearing; takes 5–6 years to first harvest'},

  {name:'Papaya',emoji:'🍈',season:'zaid',type:'fruit',bg:'#FFF9C4',
   sowMonths:[], isPerennial:true,
   N:[50,90],P:[30,60],K:[50,100],pH:[6,7],T:[25,38],H:[60,90],R:[100,180],
   tip:'Papaya is fast-growing but frost-sensitive. Avoid waterlogging at all costs.',
   altSeason:'Zaid',altSeasonIcon:'☀️',altSeasonDesc:'Fruits in 6–9 months; year-round in tropical climates'},

  {name:'Orange',emoji:'🍊',season:'rabi',type:'fruit',bg:'#FFF3E0',
   sowMonths:[], isPerennial:true,
   N:[40,80],P:[20,50],K:[40,80],pH:[5.5,7.5],T:[15,30],H:[50,75],R:[100,180],
   tip:'Orange trees need a mild cool period to induce flowering. Avoid saline soils.',
   altSeason:'Rabi',altSeasonIcon:'❄️',altSeasonDesc:'Harvested November–March depending on variety'},

  {name:'Apple',emoji:'🍎',season:'rabi',type:'fruit',bg:'#FCE4EC',
   sowMonths:[], isPerennial:true,
   N:[40,70],P:[20,50],K:[40,80],pH:[5.5,7],T:[8,20],H:[50,80],R:[100,200],
   tip:'Apple requires chilling hours (below 7°C) to break dormancy and set fruit.',
   altSeason:'Rabi',altSeasonIcon:'❄️',altSeasonDesc:'Harvested August–October in northern highlands'},

  {name:'Grapes',emoji:'🍇',season:'rabi',type:'fruit',bg:'#EDE7F6',
   sowMonths:[], isPerennial:true,
   N:[30,70],P:[20,50],K:[30,70],pH:[5.5,7.5],T:[15,30],H:[50,80],R:[50,150],
   tip:'Grapes need well-drained sandy loam. Drip irrigation prevents fungal diseases.',
   altSeason:'Rabi',altSeasonIcon:'🍇',altSeasonDesc:'Harvested February–March (India); June–September (temperate)'},

  {name:'Pomegranate',emoji:'🍎',season:'zaid',type:'fruit',bg:'#FCE4EC',
   sowMonths:[], isPerennial:true,
   N:[40,70],P:[20,50],K:[30,60],pH:[5.5,7.5],T:[25,38],H:[40,70],R:[50,150],
   tip:'Pomegranate is drought-hardy. Moderate water stress during fruit development improves colour and aril quality.',
   altSeason:'Zaid',altSeasonIcon:'☀️',altSeasonDesc:'Harvested August–February; two crops possible per year'},

  {name:'Jute',emoji:'🪢',season:'kharif',type:'fibre',bg:'#F1F8E9',
   sowMonths:[3,4,5], isPerennial:false,
   N:[60,100],P:[30,60],K:[30,60],pH:[6,7.5],T:[24,37],H:[70,90],R:[150,250],
   tip:'Jute thrives in humid, warm conditions with high rainfall. Retting quality depends on clean water.',
   altSeason:'Kharif',altSeasonIcon:'🌧️',altSeasonDesc:'Sown March–May, harvested July–September'},

  {name:'Kidneybeans',emoji:'🫘',season:'kharif',type:'pulse',bg:'#FFEBEE',
   sowMonths:[6,7], isPerennial:false,
   N:[15,40],P:[30,70],K:[15,40],pH:[5.5,7.5],T:[15,28],H:[40,70],R:[80,150],
   tip:'Kidney beans fix nitrogen. Avoid heavy clay soils — root rot is the main risk.',
   altSeason:'Kharif',altSeasonIcon:'🌧️',altSeasonDesc:'Sown June–July, harvested September–October'},

  {name:'Mothbeans',emoji:'🫘',season:'kharif',type:'pulse',bg:'#FFF8E1',
   sowMonths:[6,7], isPerennial:false,
   N:[10,30],P:[20,50],K:[15,35],pH:[6,8],T:[25,38],H:[30,60],R:[30,80],
   tip:'Moth bean is extremely drought-tolerant — ideal for arid and semi-arid regions.',
   altSeason:'Kharif',altSeasonIcon:'☀️',altSeasonDesc:'Sown June–July, harvested August–September'},
];
