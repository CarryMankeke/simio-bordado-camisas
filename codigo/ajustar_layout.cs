// Lab 1 v5: post-proceso por API del modelo con íconos 3D. uso: ajustar_layout.exe <entrada.spfx> <salida.spfx|-> [layout] [reps]
// Con "layout" reubica los objetos (sin tocar tamaños ni lógica); siempre corre el experimento y muestra las réplicas.
using System; using System.Linq; using System.Reflection; using System.Globalization; using SimioAPI;
class P{
 static CultureInfo ci=CultureInfo.InvariantCulture;
 static string F(double v)=>v.ToString("F2",ci);
 static void Main(string[] a){
 try{
  foreach(var f in System.IO.Directory.GetFiles(AppContext.BaseDirectory,"SQLitePCLRaw.batteries*.dll")){ var asm=Assembly.LoadFrom(f); foreach(var t in asm.GetTypes()) if(t.Name.StartsWith("Batteries")) t.GetMethod("Init").Invoke(null,null); }
  SimioProjectFactory.SetExtensionsPath(@"C:\Program Files\Simio LLC\Simio");
  string[] w; var proj=SimioProjectFactory.LoadProject(a[0], out w); foreach(var x in w) Console.WriteLine("W "+x);
  var model=proj.Models["Model"]; var io=model.Facility.IntelligentObjects;
  bool lay=a.Length>2 && a[2]=="layout"; int reps=a.Length>3?int.Parse(a[3]):10;
  if(lay){
   // x a la derecha, z hacia abajo (m). Flujo de izquierda a derecha; OtroCentro abajo a la izquierda.
   var pos=new (string n,double x,double z)[]{("Llegadas",-15,0),("Camisa",-17,-3),("AlmacenTemporal",-6,0),("Bordado1",2,-3.5),("Bordado2",2,0),("Bordado3",2,3.5),("Despacho",13,0),("OtroCentro",-11,8)};
   foreach(var p in pos){ var o=io[p.n]; if(o==null){Console.WriteLine("NOOBJ "+p.n);continue;} o.Location=new FacilityLocation(p.x,o.Location.Y,p.z); }
   foreach(var pr in model.GetType().GetInterfaces().SelectMany(i=>i.GetProperties())) if(pr.Name=="Description"||pr.Name=="Author") Console.WriteLine("MODELPROP "+pr.Name+" rw="+pr.CanWrite);
  }
  foreach(var o in io) if(!(o is ILinkObject) && !o.ObjectName.Contains("@")) Console.WriteLine("GEO "+o.ObjectName+" loc="+F(o.Location.X)+","+F(o.Location.Z)+" size="+F(o.Size.Length)+"x"+F(o.Size.Width)+"x"+F(o.Size.Height));
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
