// Lab 1 v6: post-proceso por API. uso: orientar_camiones.exe <entrada.spfx> <salida.spfx|-> [camiones|ver] [reps]
// "camiones": orienta los 3 camiones (Yaw, en grados; 90 = mirando a +X) y reubica OtroCentro bajo el almacén.
// Siempre corre el experimento "Escenarios" y muestra las réplicas en CSV.
using System; using System.Linq; using System.Reflection; using System.Globalization; using SimioAPI;
class P{
 static CultureInfo ci=CultureInfo.InvariantCulture;
 static string F(double v)=>v.ToString("F2",ci);
 static void Main(string[] a){
 try{
  foreach(var f in System.IO.Directory.GetFiles(AppContext.BaseDirectory,"SQLitePCLRaw.batteries*.dll")){ var asm=Assembly.LoadFrom(f); foreach(var tb in asm.GetTypes()) if(tb.Name.StartsWith("Batteries")) tb.GetMethod("Init").Invoke(null,null); }
  SimioProjectFactory.SetExtensionsPath(@"C:\Program Files\Simio LLC\Simio");
  string[] w; var proj=SimioProjectFactory.LoadProject(a[0], out w); foreach(var x in w) Console.WriteLine("W "+x);
  var model=proj.Models["Model"]; var io=model.Facility.IntelligentObjects;
  string modo=a.Length>2?a[2]:"ver"; int reps=a.Length>3?int.Parse(a[3]):10;
  void Geo(string tag){ foreach(var o in io) if(!(o is ILinkObject)) Console.WriteLine(tag+" "+o.ObjectName+" loc="+F(o.Location.X)+","+F(o.Location.Z)+" yaw="+F(o.Yaw)+" size="+F(o.Size.Length)+"x"+F(o.Size.Width)+"x"+F(o.Size.Height)); }
  Geo("ANTES");
  if(modo=="camiones"){
   // Llegadas: camión en retroceso a la izquierda (cabina hacia -X, la carga se baja por atrás hacia la línea).
   var lleg=io["Llegadas"]; lleg.Location=new FacilityLocation(-15,0,0); lleg.Yaw=270;
   var outL=io["Output@Llegadas"]; double d=Math.Abs(outL.Location.X-lleg.Location.X)+Math.Abs(outL.Location.Z-lleg.Location.Z);
   outL.Location=new FacilityLocation(lleg.Location.X+lleg.Size.Length/2,0,0);
   Console.WriteLine("nodo salida Llegadas: d="+F(d)+" -> "+F(outL.Location.X)+","+F(outL.Location.Z));
   // Despacho: camión saliendo hacia la derecha (cabina hacia +X).
   var des=io["Despacho"]; des.Location=new FacilityLocation(13,0,0); des.Yaw=90;
   // OtroCentro: camión bajo el almacén, saliendo hacia abajo de la pantalla (cabina hacia +Z).
   var otr=io["OtroCentro"]; otr.Location=new FacilityLocation(-6,0,8); otr.Yaw=180;
   io["Camisa"].Location=new FacilityLocation(-15,0,-3.5);
   Geo("DESPUES");
  }
  var ex=model.Experiments["Escenarios"]; ex.DefaultReplicationsRequired=reps;
  Console.WriteLine("errors="+model.Errors.Count); foreach(var e in model.Errors) Console.WriteLine("ERR "+e.ErrorText+" | "+e.ObjectName);
  var t0=DateTime.Now; ex.Reset(); ex.Run(); Console.WriteLine("ran s="+(DateTime.Now-t0).TotalSeconds.ToString("F1",ci));
  Console.WriteLine("CSV,Escenario,Replica,"+string.Join(",",ex.Responses.Select(r=>r.Name)));
  foreach(var sc in ex.Scenarios) for(int i=1;i<=sc.ReplicationsCompleted;i++){
   var vals=ex.Responses.Select(r=>{double v=0; sc.GetResponseValueForReplication(r,i,ref v); return v.ToString("R",ci);});
   Console.WriteLine("CSV,"+sc.Name+","+i+","+string.Join(",",vals)); }
  if(a[1]!="-"){ bool ok=SimioProjectFactory.SaveProject(proj,a[1],out w); Console.WriteLine("saved="+ok); foreach(var x in w) Console.WriteLine("W "+x); }
 }catch(Exception e){Console.WriteLine("EXC "+e);}
 SimioProjectFactory.Shutdown(); Console.WriteLine("FIN");
}}
