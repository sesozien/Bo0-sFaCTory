import { StatusBar } from 'expo-status-bar';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

type Product = {
  id: string;
  name: string;
  price: string;
  notes: string;
  imageUri: string;
  approved: boolean;
};

type CropBox = { x: number; y: number; width: number; height: number };

const CATALOG_KEY = 'bo0_mobile_catalog_v1';
const RED = '#e3484d';
const BG = '#101217';
const PANEL = '#191c24';
const MUTED = '#9ea4b4';

export default function App() {
  const [tab, setTab] = useState<'catalog' | 'crop' | 'settings'>('catalog');
  const [products, setProducts] = useState<Product[]>([]);
  const [draftName, setDraftName] = useState('');
  const [draftPrice, setDraftPrice] = useState('');
  const [draftNotes, setDraftNotes] = useState('');
  const [draftImage, setDraftImage] = useState('');
  const [cropImage, setCropImage] = useState('');
  const [cropBox, setCropBox] = useState<CropBox>({ x: 0, y: 0, width: 1000, height: 1000 });
  const [sourceSize, setSourceSize] = useState({ width: 1000, height: 1000 });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(CATALOG_KEY).then((value) => {
      if (value) setProducts(JSON.parse(value));
    });
  }, []);

  const persist = async (next: Product[]) => {
    setProducts(next);
    await AsyncStorage.setItem(CATALOG_KEY, JSON.stringify(next));
  };

  const chooseImage = async (forCrop = false) => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1,
      allowsEditing: false,
    });
    if (result.canceled || !result.assets[0]) return;
    const asset = result.assets[0];
    if (forCrop) {
      setCropImage(asset.uri);
      setSourceSize({ width: asset.width || 1000, height: asset.height || 1000 });
      setCropBox({ x: 0, y: 0, width: asset.width || 1000, height: asset.height || 1000 });
      setTab('crop');
    } else {
      setDraftImage(asset.uri);
    }
  };

  const addProduct = async () => {
    if (!draftName.trim() || !draftImage) {
      Alert.alert('بيانات ناقصة', 'اكتب اسم المنتج واختر صورته أولًا.');
      return;
    }
    if (products.some((item) => item.name.trim().toLowerCase() === draftName.trim().toLowerCase())) {
      Alert.alert('المنتج موجود', 'يوجد منتج بنفس الاسم في الكتالوج.');
      return;
    }
    const next = [{ id: Date.now().toString(), name: draftName.trim(), price: draftPrice.trim(), notes: draftNotes.trim(), imageUri: draftImage, approved: false }, ...products];
    await persist(next);
    setDraftName('');
    setDraftPrice('');
    setDraftNotes('');
    setDraftImage('');
    Alert.alert('تم الحفظ', 'أضيف المنتج إلى الكتالوج المحلي.');
  };

  const applyCrop = async () => {
    if (!cropImage) return;
    setBusy(true);
    try {
      const result = await ImageManipulator.manipulateAsync(cropImage, [{ crop: { originX: cropBox.x, originY: cropBox.y, width: cropBox.width, height: cropBox.height } }], { compress: 1, format: ImageManipulator.SaveFormat.PNG });
      setDraftImage(result.uri);
      setCropImage(result.uri);
      setSourceSize({ width: result.width, height: result.height });
      setCropBox({ x: 0, y: 0, width: result.width, height: result.height });
      setTab('catalog');
      Alert.alert('تم القص', 'تم حفظ الصورة بصيغة PNG بدون ضغط فاقد للجودة. يمكنك الآن إدخال بيانات المنتج.');
    } catch {
      Alert.alert('تعذر القص', 'جرّب صورة أخرى أو صغّر حدود القص.');
    } finally {
      setBusy(false);
    }
  };

  const adjustCrop = (field: keyof CropBox, amount: number) => {
    setCropBox((current) => {
      const next = { ...current, [field]: Math.round(current[field] + amount) };
      next.x = Math.max(0, Math.min(next.x, sourceSize.width - 1));
      next.y = Math.max(0, Math.min(next.y, sourceSize.height - 1));
      next.width = Math.max(1, Math.min(next.width, sourceSize.width - next.x));
      next.height = Math.max(1, Math.min(next.height, sourceSize.height - next.y));
      return next;
    });
  };

  const exportPdf = async (approvedOnly = false) => {
    const list = approvedOnly ? products.filter((item) => item.approved) : products;
    if (!list.length) {
      Alert.alert('الكتالوج فارغ', 'أضف منتجًا واحدًا على الأقل.');
      return;
    }
    setBusy(true);
    try {
      const cards = await Promise.all(list.map(async (item) => {
        let image = '';
        try {
          const base64 = await FileSystem.readAsStringAsync(item.imageUri, { encoding: FileSystem.EncodingType.Base64 });
          image = `<img src="data:image/jpeg;base64,${base64}" />`;
        } catch {
          image = '';
        }
        return `<article><div class="photo">${image}</div><h2>${escapeHtml(item.name)}</h2><strong>${escapeHtml(item.price || 'السعر عند الطلب')} جنيه</strong><p>${escapeHtml(item.notes)}</p></article>`;
      }));
      const html = `<html dir="rtl"><head><meta charset="utf-8"><style>body{font-family:Arial;background:#fff;color:#171923;padding:20px}h1{color:#d94248;border-bottom:3px solid #d94248;padding-bottom:10px}main{display:flex;flex-wrap:wrap;gap:12px}article{width:46%;border:1px solid #ddd;border-radius:12px;padding:10px;margin-bottom:12px;box-sizing:border-box}.photo{height:170px;text-align:center}.photo img{max-width:100%;max-height:170px}h2{font-size:18px;margin:8px 0}strong{color:#d94248;font-size:17px}p{color:#555}</style></head><body><h1>كتالوج المنتجات</h1><main>${cards.join('')}</main></body></html>`;
      const file = await Print.printToFileAsync({ html });
      if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(file.uri, { mimeType: 'application/pdf', dialogTitle: 'مشاركة كتالوج المنتجات' });
    } catch {
      Alert.alert('تعذر إنشاء PDF', 'تأكد من وجود منتجات وصور محفوظة.');
    } finally {
      setBusy(false);
    }
  };

  const toggleApproved = async (id: string) => {
    await persist(products.map((item) => item.id === id ? { ...item, approved: !item.approved } : item));
  };

  const deleteProduct = (id: string) => {
    Alert.alert('حذف المنتج', 'هل تريد حذف هذا المنتج من الكتالوج؟', [
      { text: 'إلغاء', style: 'cancel' },
      { text: 'حذف', style: 'destructive', onPress: () => persist(products.filter((item) => item.id !== id)) },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <View style={styles.header}><View><Text style={styles.kicker}>Bo0 • Factory</Text><Text style={styles.title}>مصنع منتجك</Text></View><View style={styles.badge}><Text style={styles.badgeText}>{products.length} منتج</Text></View></View>
      <View style={styles.body}>
        {tab === 'catalog' && <CatalogScreen {...{ products, draftImage, draftName, draftPrice, draftNotes, setDraftName, setDraftPrice, setDraftNotes, chooseImage, addProduct, toggleApproved, deleteProduct, exportPdf, busy, setTab }} />}
        {tab === 'crop' && <CropScreen {...{ cropImage, cropBox, sourceSize, setCropBox, adjustCrop, chooseImage, applyCrop, busy }} />}
        {tab === 'settings' && <SettingsScreen products={products} />}
      </View>
      <View style={styles.nav}>
        <NavButton icon="🗂️" label="الكتالوج" active={tab === 'catalog'} onPress={() => setTab('catalog')} />
        <NavButton icon="✂️" label="قص صورة" active={tab === 'crop'} onPress={() => chooseImage(true)} />
        <NavButton icon="⚙️" label="الإعدادات" active={tab === 'settings'} onPress={() => setTab('settings')} />
      </View>
    </SafeAreaView>
  );
}

function CatalogScreen(props: any) {
  return <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
    <Text style={styles.sectionTitle}>الكتالوج المحلي</Text>
    <Text style={styles.helper}>أضف المنتجات وعدّلها من الهاتف. البيانات تحفظ داخل الجهاز.</Text>
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>إضافة منتج سريع</Text>
      <Pressable style={styles.imagePicker} onPress={() => props.chooseImage(false)}>{props.draftImage ? <Image source={{ uri: props.draftImage }} style={styles.draftImage} /> : <><Text style={styles.plus}>＋</Text><Text style={styles.imagePickerText}>اختر صورة المنتج</Text></>}</Pressable>
      <TextInput style={styles.input} placeholder="اسم المنتج" placeholderTextColor="#73798a" value={props.draftName} onChangeText={props.setDraftName} />
      <TextInput style={styles.input} placeholder="السعر" placeholderTextColor="#73798a" keyboardType="decimal-pad" value={props.draftPrice} onChangeText={props.setDraftPrice} />
      <TextInput style={[styles.input, styles.notes]} placeholder="المقاسات والألوان والخامة" placeholderTextColor="#73798a" multiline value={props.draftNotes} onChangeText={props.setDraftNotes} />
      <Pressable style={styles.primary} onPress={props.addProduct}><Text style={styles.primaryText}>حفظ المنتج</Text></Pressable>
    </View>
    <View style={styles.rowBetween}><Text style={styles.sectionTitle}>المنتجات ({props.products.length})</Text><Pressable onPress={() => props.exportPdf(false)}><Text style={styles.link}>PDF الكل</Text></Pressable></View>
    <Pressable style={styles.secondary} onPress={() => props.exportPdf(true)}><Text style={styles.secondaryText}>📄 مشاركة PDF المعتمد فقط</Text></Pressable>
    {props.products.map((item: Product) => <View style={styles.product} key={item.id}><Image source={{ uri: item.imageUri }} style={styles.productImage} /><View style={styles.productInfo}><Text style={styles.productName}>{item.name}</Text><Text style={styles.price}>{item.price || 'السعر عند الطلب'} جنيه</Text><Text style={styles.productNotes} numberOfLines={2}>{item.notes || 'بدون ملاحظات'}</Text><View style={styles.actions}><Pressable onPress={() => props.toggleApproved(item.id)}><Text style={item.approved ? styles.approved : styles.action}>{item.approved ? '✓ معتمد' : 'اعتماد'}</Text></Pressable><Pressable onPress={() => props.deleteProduct(item.id)}><Text style={styles.delete}>حذف</Text></Pressable></View></View></View>)}
    {!props.products.length && <Text style={styles.empty}>لسه مفيش منتجات. ابدأ بإضافة أول صورة.</Text>}
  </ScrollView>;
}

function CropScreen({ cropImage, cropBox, sourceSize, setCropBox, adjustCrop, chooseImage, applyCrop, busy }: any) {
  const guide = useMemo(() => ({ left: `${(cropBox.x / sourceSize.width) * 100}%`, top: `${(cropBox.y / sourceSize.height) * 100}%`, width: `${(cropBox.width / sourceSize.width) * 100}%`, height: `${(cropBox.height / sourceSize.height) * 100}%` }), [cropBox, sourceSize]);
  return <ScrollView contentContainerStyle={styles.scroll}><Text style={styles.sectionTitle}>قص الصورة بالإحداثيات</Text><Text style={styles.helper}>الإطار الأصفر هو الجزء الذي سيتم استخراجه. الصورة الأصلية لا يتم تصغيرها.</Text>{cropImage ? <><View style={styles.previewFrame}><Image source={{ uri: cropImage }} style={styles.previewImage} resizeMode="contain" /><View style={[styles.cropGuide, guide as any]}><View style={styles.crossH} /><View style={styles.crossV} /></View></View><Text style={styles.coordinates}>X1 {cropBox.x}  •  Y1 {cropBox.y}  •  X2 {cropBox.x + cropBox.width}  •  Y2 {cropBox.y + cropBox.height}</Text><View style={styles.coordGrid}>{(['x', 'y', 'width', 'height'] as const).map((field) => <View style={styles.coordCell} key={field}><Text style={styles.coordLabel}>{field === 'x' ? 'بداية X' : field === 'y' ? 'بداية Y' : field === 'width' ? 'العرض' : 'الارتفاع'}</Text><TextInput style={styles.coordInput} keyboardType="number-pad" value={String(cropBox[field])} onChangeText={(value) => setCropBox({ ...cropBox, [field]: Math.max(1, Number(value) || 0) })} /></View>)}</View><View style={styles.nudgeRow}>{(['x', 'y', 'width', 'height'] as const).map((field) => <View style={styles.nudge} key={field}><Text style={styles.nudgeLabel}>{field === 'x' ? 'X' : field === 'y' ? 'Y' : field === 'width' ? 'العرض' : 'الطول'}</Text><View style={styles.nudgeButtons}><Pressable style={styles.smallButton} onPress={() => adjustCrop(field, -10)}><Text style={styles.smallButtonText}>−</Text></Pressable><Pressable style={styles.smallButton} onPress={() => adjustCrop(field, 10)}><Text style={styles.smallButtonText}>＋</Text></Pressable></View></View>)}</View><Pressable style={styles.primary} onPress={applyCrop} disabled={busy}><Text style={styles.primaryText}>{busy ? 'جاري القص...' : 'استخراج PNG بجودة كاملة'}</Text></Pressable></> : <Pressable style={styles.emptyCrop} onPress={() => chooseImage(true)}><Text style={styles.plus}>＋</Text><Text style={styles.imagePickerText}>اختر صورة لبدء القص</Text></Pressable>}</ScrollView>;
}

function SettingsScreen({ products }: { products: Product[] }) { return <ScrollView contentContainerStyle={styles.scroll}><Text style={styles.sectionTitle}>إعدادات التطبيق</Text><View style={styles.panel}><Text style={styles.panelTitle}>حفظ محلي</Text><Text style={styles.helper}>المنتجات محفوظة على الهاتف تلقائيًا وعددها الآن {products.length}.</Text><Text style={styles.helper}>المونتاج والقص والكتالوج وPDF تعمل بدون إنترنت. تحليل Gemini ورادار تيليجرام يحتاجان اتصالًا عند الاستخدام.</Text></View><View style={styles.panel}><Text style={styles.panelTitle}>نسخة Android التجريبية</Text><Text style={styles.helper}>هذه نسخة موبايل خفيفة بواجهة عربية RTL، وتستعد للبناء كـ APK من Expo/EAS.</Text></View></ScrollView>; }

function NavButton({ icon, label, active, onPress }: { icon: string; label: string; active: boolean; onPress: () => void }) { return <Pressable style={[styles.navButton, active && styles.navActive]} onPress={onPress}><Text style={styles.navIcon}>{icon}</Text><Text style={[styles.navLabel, active && styles.navLabelActive]}>{label}</Text></Pressable>; }
function escapeHtml(value: string) { return value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char] as string)); }

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: BG }, body: { flex: 1 }, header: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, kicker: { color: RED, fontSize: 12, fontWeight: '800', textAlign: 'right' }, title: { color: '#fff', fontSize: 25, fontWeight: '900', textAlign: 'right' }, badge: { backgroundColor: '#29212a', borderRadius: 18, paddingHorizontal: 13, paddingVertical: 8 }, badgeText: { color: '#ffc3c4', fontWeight: '700' }, scroll: { padding: 18, paddingBottom: 30 }, sectionTitle: { color: '#fff', fontSize: 21, fontWeight: '900', textAlign: 'right', marginBottom: 5 }, helper: { color: MUTED, textAlign: 'right', lineHeight: 21, marginBottom: 14 }, panel: { backgroundColor: PANEL, borderRadius: 18, padding: 15, marginBottom: 16 }, panelTitle: { color: '#fff', fontSize: 16, fontWeight: '800', textAlign: 'right', marginBottom: 12 }, imagePicker: { height: 145, borderRadius: 14, borderWidth: 1, borderColor: '#3a3f4e', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', marginBottom: 12, overflow: 'hidden' }, draftImage: { width: '100%', height: '100%' }, plus: { fontSize: 34, color: RED, lineHeight: 38 }, imagePickerText: { color: '#d9dce4', fontWeight: '700' }, input: { backgroundColor: '#242832', color: '#fff', borderRadius: 12, paddingHorizontal: 13, paddingVertical: 12, marginBottom: 9, textAlign: 'right', fontSize: 15 }, notes: { minHeight: 74, textAlignVertical: 'top' }, primary: { backgroundColor: RED, borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginTop: 4 }, primaryText: { color: '#fff', fontWeight: '900', fontSize: 15 }, secondary: { backgroundColor: '#272b36', borderRadius: 12, paddingVertical: 12, alignItems: 'center', marginBottom: 14 }, secondaryText: { color: '#fff', fontWeight: '800' }, rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }, link: { color: '#ff9b9e', fontWeight: '800' }, product: { backgroundColor: PANEL, borderRadius: 16, padding: 11, marginBottom: 10, flexDirection: 'row', gap: 12 }, productImage: { width: 92, height: 92, borderRadius: 12, backgroundColor: '#262a34' }, productInfo: { flex: 1, alignItems: 'flex-end' }, productName: { color: '#fff', fontSize: 16, fontWeight: '900', textAlign: 'right' }, price: { color: '#ff9b9e', fontWeight: '800', marginTop: 3 }, productNotes: { color: MUTED, textAlign: 'right', marginTop: 4 }, actions: { flexDirection: 'row', gap: 18, marginTop: 8 }, action: { color: '#cbd0da', fontWeight: '800' }, approved: { color: '#6ee7a1', fontWeight: '900' }, delete: { color: '#ff777c', fontWeight: '800' }, empty: { color: MUTED, textAlign: 'center', marginTop: 35 }, nav: { height: 78, backgroundColor: '#171920', borderTopWidth: 1, borderTopColor: '#2b2f3b', flexDirection: 'row-reverse', justifyContent: 'space-around', alignItems: 'center', paddingBottom: 7 }, navButton: { alignItems: 'center', paddingHorizontal: 18, paddingVertical: 7, borderRadius: 15 }, navActive: { backgroundColor: '#382126' }, navIcon: { fontSize: 20 }, navLabel: { color: MUTED, fontSize: 12, marginTop: 3 }, navLabelActive: { color: '#ffb0b2', fontWeight: '800' }, previewFrame: { height: 330, backgroundColor: '#050608', borderRadius: 16, overflow: 'hidden', marginTop: 12, position: 'relative' }, previewImage: { width: '100%', height: '100%' }, cropGuide: { position: 'absolute', borderColor: '#ffd54a', borderWidth: 3, backgroundColor: 'rgba(255,213,74,0.08)' }, crossH: { position: 'absolute', left: 0, right: 0, top: '50%', height: 1, backgroundColor: 'rgba(255,255,255,0.6)' }, crossV: { position: 'absolute', top: 0, bottom: 0, left: '50%', width: 1, backgroundColor: 'rgba(255,255,255,0.6)' }, coordinates: { color: '#ffd54a', textAlign: 'center', fontWeight: '800', marginVertical: 12 }, coordGrid: { flexDirection: 'row-reverse', flexWrap: 'wrap', gap: 9, marginBottom: 12 }, coordCell: { width: '48%' }, coordLabel: { color: MUTED, textAlign: 'right', fontSize: 12, marginBottom: 4 }, coordInput: { backgroundColor: '#242832', color: '#fff', borderRadius: 10, padding: 10, textAlign: 'center' }, nudgeRow: { flexDirection: 'row-reverse', justifyContent: 'space-between', marginBottom: 15 }, nudge: { alignItems: 'center' }, nudgeLabel: { color: MUTED, fontSize: 12, marginBottom: 5 }, nudgeButtons: { flexDirection: 'row', gap: 5 }, smallButton: { backgroundColor: '#303542', width: 35, height: 32, borderRadius: 9, justifyContent: 'center', alignItems: 'center' }, smallButtonText: { color: '#fff', fontSize: 21 }, emptyCrop: { height: 260, borderRadius: 16, borderWidth: 1, borderColor: '#3a3f4e', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', marginTop: 16 },
});
