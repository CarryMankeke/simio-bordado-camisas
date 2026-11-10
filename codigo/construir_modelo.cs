// Lab 1 v4 (10 nov 2026): rehace el modelo con el feedback del ayudante (clase del 9 nov).
//  - Almacenamiento temporal como objeto propio: Server de capacidad 10 y tiempo 0 (sin buffers).
//  - Bordadoras: 3 Servers de capacidad 1 en paralelo; la propiedad Maquinas (1/2/3) habilita cuantas trabajan.
//  - Connectors (instantaneos), objetos a escala en la cuadricula de 1 m.
// uso: construir_modelo.exe <base.spfx> <salida.spfx> [lista|peso] [reps]
using System; using System.Linq; using System.Reflection; using System.Globalization; using SimioAPI;
class P{
 static CultureInfo ci=CultureInfo.InvariantCulture;
 static void Set(IIntelligentObject o,string prop,string val){ var p=o.Properties[prop]; if(p==null){Console.WriteLine("NOPROP "+o.ObjectName+"."+prop);return;} try{ p.Value=val; }catch(Exception e){ Console.WriteLine("SETEXC "+o.ObjectName+"."+prop+" "+e.Message); } Console.WriteLine("set "+o.ObjectName+"."+prop+"="+p.Value+(p.Unit!=null?" ["+p.Unit+"]":"")); }
 static void Seg(IIntelligentObject o,string prop){ ((ITimeUnit)o.Properties[prop].Unit).Time=TimeUnit.Seconds; }
 static IIntelligentObject Obj(IIntelligentObjects io,string tipo,string nombre,double x,double z,double l,double w,double h){
  var o=io.CreateObject(tipo,new FacilityLocation(x,0,z)); o.ObjectName=nombre; o.Size=new FacilitySize(l,w,h); return o; }
 static void Main(string[] a){
 try{
  foreach(var f in System.IO.Directory.GetFiles(AppContext.BaseDirectory,"SQLitePCLRaw.batteries*.dll")){ var asm=Assembly.LoadFrom(f); foreach(var t in asm.GetTypes()) if(t.Name.StartsWith("Batteries")) t.GetMethod("Init").Invoke(null,null); }
  SimioProjectFactory.SetExtensionsPath(@"C:\Program Files\Simio LLC\Simio");
  Console.WriteLine("IsLicensed="+SimioProjectFactory.IsLicensed);
  string modo=a.Length>2?a[2]:"lista"; int reps=a.Length>3?int.Parse(a[3]):10;
  string[] w; var proj=SimioProjectFactory.LoadProject(a[0], out w);
  foreach(var x in w) Console.WriteLine("W "+x);
  var model=proj.Models["Model"]; var io=model.Facility.IntelligentObjects;
  // 1) vaciar el modelo anterior (links, objetos, experimentos, listas)
  while(model.Experiments.Count>0) model.Experiments.RemoveAt(0);
  foreach(var o in io.ToList().Where(o=>o is ILinkObject)) io.Remove(o);
  foreach(var o in io.ToList().Where(o=>!o.ObjectName.Contains("@"))) io.Remove(o);
  foreach(var o in io.ToList()) try{io.Remove(o);}catch{}
  while(model.NamedLists.Count>0) model.NamedLists.RemoveAt(0);
  Console.WriteLine("quedan="+io.Count);
  var pd=model.PropertyDefinitions["Maquinas"]; if(pd==null){ model.PropertyDefinitions.AddRealProperty("Maquinas",3); pd=model.PropertyDefinitions["Maquinas"]; }
  foreach(var pp in pd.GetType().GetInterfaces().SelectMany(i=>i.GetProperties())) if(pp.Name.Contains("Default")){ try{ Console.WriteLine("PD "+pp.Name+"="+pp.GetValue(pd)); if(pp.CanWrite && pp.PropertyType==typeof(string)) { pp.SetValue(pd,"3"); Console.WriteLine("PD "+pp.Name+" -> "+pp.GetValue(pd)); } if(pp.CanWrite && pp.PropertyType==typeof(double)) { pp.SetValue(pd,3.0); Console.WriteLine("PD "+pp.Name+" -> "+pp.GetValue(pd)); } }catch(Exception e){Console.WriteLine("PDEXC "+pp.Name+" "+e.Message);} }
  if(!proj.Libraries.Any(l=>l.Name.Contains("Standard"))){ var L=proj.Libraries.LoadFromFile(@"C:\Program Files\Simio LLC\Simio\Libraries\StandardLibrary.spfx", default(LoadLibraryOptions)); Console.WriteLine("loaded "+L?.Name); }
  // 2) objetos a escala (x a la derecha, z hacia abajo en planta; 1 cuadro = 1 m)
  var camisa=io.CreateObject("ModelEntity",new FacilityLocation(-14,0,-3)); camisa.ObjectName="Camisa"; camisa.Size=new FacilitySize(0.5,0.4,0.1);
  var src=Obj(io,"Source","Llegadas",-13,0,1.5,1,1);
  var alm=Obj(io,"Server","AlmacenTemporal",-6,0,3,2,1.5);
  var b1=Obj(io,"Server","Bordado1",2,-3,1.5,1,1.2);
  var b2=Obj(io,"Server","Bordado2",2,0,1.5,1,1.2);
  var b3=Obj(io,"Server","Bordado3",2,3,1.5,1,1.2);
  var des=Obj(io,"Sink","Despacho",9,0,1.5,1,1);
  var otr=Obj(io,"Sink","OtroCentro",-9,6,1.5,1,1);
  Set(src,"EntityType","Camisa"); Set(src,"InterarrivalTime","Random.Exponential(60)"); Seg(src,"InterarrivalTime");
  Set(alm,"InitialCapacity","10"); Set(alm,"ProcessingTime","0"); Set(alm,"InputBufferCapacity","0"); Set(alm,"OutputBufferCapacity","0");
  var bs=new[]{b1,b2,b3};
  for(int i=0;i<3;i++){ var b=bs[i];
   Set(b,"InitialCapacity", i==0?"1":"Math.If(Maquinas >= "+(i+1)+", 1, 0)");
   Set(b,"ProcessingTime","Random.Normal(150,4)"); Seg(b,"ProcessingTime");
   Set(b,"InputBufferCapacity","0"); }
  // 3) enlaces (Connectors) y decisiones
  INodeObject N(string n)=>(INodeObject)io[n];
  var outS=N("Output@Llegadas"); var outA=N("Output@AlmacenTemporal");
  Set((IIntelligentObject)outS,"OutboundLinkRule","By Link Weight");
  var cA=io.CreateLink("Connector",outS,N("Input@AlmacenTemporal"),null); cA.ObjectName="AlAlmacen";
  var cD=io.CreateLink("Connector",outS,N("Input@OtroCentro"),null); cD.ObjectName="Desvio";
  Set(cA,"SelectionWeight","AlmacenTemporal.Capacity.Remaining > 0");
  Set(cD,"SelectionWeight","AlmacenTemporal.Capacity.Remaining <= 0");
  var oa=(IIntelligentObject)outA;
  Set(oa,"TransferInConstraintsType","Custom Condition");
  Set(oa,"TransferInCondition","Bordado1.Capacity.Remaining + Bordado2.Capacity.Remaining + Bordado3.Capacity.Remaining > 0");
  for(int i=0;i<3;i++){ var c=io.CreateLink("Connector",outA,N("Input@Bordado"+(i+1)),null); c.ObjectName="AMaquina"+(i+1);
   if(modo=="peso") Set(c,"SelectionWeight","Bordado"+(i+1)+".Capacity.Remaining > 0");
   var s=io.CreateLink("Connector",N("Output@Bordado"+(i+1)),N("Input@Despacho"),null); s.ObjectName="Salida"+(i+1); }
  if(modo=="peso") Set(oa,"OutboundLinkRule","By Link Weight");
  else {
   var lst=model.NamedLists.AddNodeList("Bordadoras");
   for(int i=0;i<3;i++){ var r=lst.Rows.Create(); var rp=r.Properties[0]; rp.Value="Input@Bordado"+(i+1); Console.WriteLine("lista "+rp.Name+"="+rp.Value); }
   Set(oa,"DestinationType","Select From List"); Set(oa,"DestinationNodeListName","Bordadoras");
   Set(oa,"DestinationSelectionGoal","Random"); Set(oa,"BlockedDestinationRule","Select Available Only");
   Set(oa,"OutboundLinkRule","Shortest Path"); }
  foreach(var o in io) Console.WriteLine("GEO "+o.ObjectName+" : "+o.TypeName+" loc="+o.Location.X.ToString("F2",ci)+","+o.Location.Z.ToString("F2",ci)+" size="+o.Size.Length.ToString("F2",ci)+"x"+o.Size.Width.ToString("F2",ci)+"x"+o.Size.Height.ToString("F2",ci));
  // 4) corrida de 8 h y experimento
  model.RunSetup.EndingTime=model.RunSetup.StartingTime.AddHours(8);
  var ex=model.Experiments.Create("Escenarios"); ex.DefaultReplicationsRequired=reps;
  ex.RunSetup.EndingTime=ex.RunSetup.StartingTime.AddHours(8);
  string[,] resp={
   {"Despachadas","Despacho.InputBuffer.NumberEntered"},
   {"Desviadas","OtroCentro.InputBuffer.NumberEntered"},
   {"Util1","Bordado1.Capacity.ScheduledUtilization"},
   {"Util2","Bordado2.Capacity.ScheduledUtilization"},
   {"Util3","Bordado3.Capacity.ScheduledUtilization"},
   {"EsperaAlm_h","AlmacenTemporal.Processing.Contents.AverageTimeWaiting"},
   {"WIPAlm","AlmacenTemporal.Processing.Contents.AverageNumberWaiting"},
   {"MaxAlm","AlmacenTemporal.Processing.Contents.MaximumNumberWaiting"},
   {"Creadas","Camisa.Population.NumberCreated"},
   {"MaxSistema","Camisa.Population.NumberInSystem.Maximum"},
   {"EnSistemaFin","Camisa.Population.NumberInSystem"},
   {"TiempoSistema_h","Camisa.Population.TimeInSystem.Average"}};
  for(int i=0;i<resp.GetLength(0);i++){ var r=ex.Responses.Create(resp[i,0]); r.Expression=resp[i,1]; }
  var ctl=ex.Controls["Maquinas"];
  while(ex.Scenarios.Count>0) ex.Scenarios.RemoveAt(0);
  foreach(var n in new[]{1,2,3}){ var sc=ex.Scenarios.Create("Maq"+n); sc.SetControlValue(ctl,n.ToString()); }
  Console.WriteLine("errors="+model.Errors.Count); foreach(var e in model.Errors) Console.WriteLine("ERR "+e.ErrorText+" | "+e.PropertyName+" | "+e.ObjectName);
  var t0=DateTime.Now; ex.Reset(); try{ ex.Run(); }catch(Exception e1){ Console.WriteLine("RUNEXC "+e1.Message); foreach(var er in model.Errors) Console.WriteLine("ERR "+er.ErrorText+" | "+er.PropertyName+" | "+er.ObjectName); }
  Console.WriteLine("ran s="+(DateTime.Now-t0).TotalSeconds.ToString("F1",ci));
  Console.WriteLine("CSV,Escenario,Replica,"+string.Join(",",ex.Responses.Select(r=>r.Name)));
  foreach(var sc in ex.Scenarios) for(int i=1;i<=sc.ReplicationsCompleted;i++){
   var vals=ex.Responses.Select(r=>{double v=0; sc.GetResponseValueForReplication(r,i,ref v); return v.ToString("R",ci);});
   Console.WriteLine("CSV,"+sc.Name+","+i+","+string.Join(",",vals)); }
  bool ok=SimioProjectFactory.SaveProject(proj,a[1],out w); Console.WriteLine("saved="+ok); foreach(var x in w) Console.WriteLine("W "+x);
 }catch(Exception e){Console.WriteLine("EXC "+e);}
 SimioProjectFactory.Shutdown();
 Console.WriteLine("FIN");
}}
