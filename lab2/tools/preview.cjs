// Serves only the editable UI directory on loopback. Ctrl+C to stop.
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../ui/source');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'};
function handler(req,res){
 let pathname;
 try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400);res.end();return;}
 const file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
 if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
 fs.readFile(file,(error,data)=>{if(error){res.writeHead(404);res.end('Not found');return;}res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(data);});
}
function start(port=4173){const server=http.createServer(handler);return new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',()=>resolve(server));});}
module.exports={start};
if(require.main===module)start(Number(process.env.PORT)||4173).then(server=>console.log(`Local preview: http://127.0.0.1:${server.address().port}`));
