use serde::Serialize;
use std::collections::BTreeMap;

const COURSES:&[&str]=&["HDL","LCD","CS101","Networks","Thesis"];
const TOPICS:&[&str]=&["binary search trees","database normalization","dynamic programming","combinational logic","regular expressions","sorting algorithms","process scheduling","finite automata","karnaugh maps","TCP handshakes","graph traversal","Boolean algebra","joins in SQL","hash tables","linked lists","SQL joins","binary trees","OSI layers","recursion","2's complement","3's complement"];
const DATES:&[&str]=&["next Monday","next Tuesday","next Wednesday","next Thursday","next Friday","next Saturday","next Sunday","today","tomorrow","yesterday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday","this week","next week","this month"];
#[derive(Debug,Clone,Serialize,PartialEq)]#[serde(untagged)]pub enum EntityValue{Text(String),Int(i64)}
pub type Entities=BTreeMap<String,EntityValue>;
fn boundary(hay:&str,needle:&str)->bool{let h=hay.to_lowercase();let n=needle.to_lowercase();h.match_indices(&n).any(|(i,_)|{let b=h.as_bytes();let end=i+n.len();(i==0||!b[i-1].is_ascii_alphanumeric())&&(end==b.len()||!b[end].is_ascii_alphanumeric())})}
fn course(t:&str)->Option<String>{COURSES.iter().find(|x|boundary(t,x)).map(|x|x.to_string())}
fn topic(t:&str)->Option<String>{let mut v=TOPICS.to_vec();v.sort_by_key(|x|std::cmp::Reverse(x.len()));v.into_iter().find(|x|boundary(t,x)).map(|x|x.to_string())}
fn date(t:&str)->Option<String>{DATES.iter().find(|x|boundary(t,x)).map(|x|x.to_string())}
fn time(t:&str)->Option<String>{let c:Vec<char>=t.to_lowercase().chars().collect();let mut i=0;while i<c.len(){if c[i].is_ascii_digit(){let s=i;while i<c.len()&&c[i].is_ascii_digit(){i+=1;}let h0:String=c[s..i].iter().collect();let mut min=0u32;if i<c.len()&&c[i]==':'{let ms=i+1;let mut j=ms;while j<c.len()&&c[j].is_ascii_digit(){j+=1;}if j>ms{min=c[ms..j].iter().collect::<String>().parse().unwrap_or(0);i=j;}}while i<c.len()&&c[i]==' ' {i+=1;}if i+1<c.len(){let ap:String=c[i..i+2].iter().collect();if (ap=="am"||ap=="pm")&&min<60{if let Ok(mut h)=h0.parse::<u32>(){if h>=1&&h<=12{if ap=="pm"&&h!=12{h+=12;}if ap=="am"&&h==12{h=0;}return Some(format!("{:02}:{:02}",h,min));}}}}}else{i+=1;}}None}
fn number_after(t:&str,kind:&str)->Option<i64>{let l=t.to_lowercase();let marker=kind.to_lowercase();if let Some(p)=l.find(&marker){let rest=&l[p+marker.len()..];let digits: String=rest.trim_start_matches(|c:char|c==' '||c=='#').chars().take_while(|c|c.is_ascii_digit()).collect();if !digits.is_empty(){return digits.parse().ok();}}None}
fn amount(t:&str)->Option<i64>{
 let l=t.to_lowercase();
 let chars:Vec<char>=l.chars().collect();
 for i in 0..chars.len(){
  if chars[i]=='₱' || (i+3<=chars.len() && chars[i..i+3].iter().collect::<String>()=="php") {
   let mut j=i+1; while j<chars.len()&&chars[j].is_whitespace(){j+=1;}
   let start=j; while j<chars.len()&&(chars[j].is_ascii_digit()||chars[j]==','){j+=1;}
   if j>start {let raw:String=chars[start..j].iter().filter(|c|**c!=',').collect();if let Ok(v)=raw.parse(){return Some(v);}}
  }
 }
 let words:Vec<&str>=l.split_whitespace().collect();
 for i in 0..words.len(){if words[i]=="pesos"||words[i]=="peso"{if i>0{let cleaned=words[i-1].replace(',', ""); if let Ok(v)=cleaned.parse::<i64>() {return Some(v);}}}}
 None
}
fn title(t:&str)->Option<String>{for marker in ["titled ","called ","named "]{if let Some(p)=t.to_lowercase().find(marker){let start=p+marker.len();let rest=&t[start..];let mut end=rest.len();for stop in [" tomorrow"," today"," on "," due "," at ",",","."]{if let Some(x)=rest.to_lowercase().find(stop){end=end.min(x);}}let s=rest[..end].trim();if !s.is_empty(){return Some(s.to_string());}}}for kw in ["lab report","project","assignment","exam","quiz","report","proposal"]{if boundary(t,kw){return Some(kw.to_string());}}None}
fn description(t:&str)->Option<String>{let l=t.to_lowercase();if let Some(p)=l.rfind(" for "){let s=t[p+5..].trim().trim_end_matches('.').trim();if !s.is_empty(){return Some(s.to_string())}}None}
fn wanted(intent:&str)->&'static[&'static str]{match intent{"CREATE_DEADLINE"=>&["course","date","time","title"],"UPDATE_DEADLINE"=>&["deadline_id","course","date","time"],"DELETE_DEADLINE"=>&["deadline_id","course"],"MARK_NO_CLASS"=>&["course","date"],"GET_COURSE_DEADLINES"=>&["course"],"RECORD_DEPOSIT"=>&["amount"],"RECORD_EXPENSE"=>&["amount","description"],"SEARCH_NOTES"|"LEARN_TOPIC"|"EXPLAIN_TOPIC"|"QUIZ_TOPIC"|"PRACTICE_TOPIC"=>&["topic"],"CREATE_NOTE"=>&["title"],"UPDATE_NOTE"=>&["note_id","title"],"DELETE_NOTE"=>&["note_id"],"CREATE_POLL"=>&["title"],"VOTE_POLL"|"DELETE_POLL"=>&["poll_id"],_=>&[]}}
pub fn extract_entities(t:&str,intent:&str)->Entities{let mut e=Entities::new();for k in wanted(intent){match *k{"course"=>if let Some(v)=course(t){e.insert(k.to_string(),EntityValue::Text(v));},"date"=>if let Some(v)=date(t){e.insert(k.to_string(),EntityValue::Text(v));},"time"=>if let Some(v)=time(t){e.insert(k.to_string(),EntityValue::Text(v));},"amount"=>if let Some(v)=amount(t){e.insert(k.to_string(),EntityValue::Int(v));},"topic"=>if let Some(v)=topic(t){e.insert(k.to_string(),EntityValue::Text(v));},"deadline_id"=>if let Some(v)=number_after(t,"deadline"){e.insert(k.to_string(),EntityValue::Int(v));},"note_id"=>if let Some(v)=number_after(t,"note"){e.insert(k.to_string(),EntityValue::Int(v));},"poll_id"=>if let Some(v)=number_after(t,"poll"){e.insert(k.to_string(),EntityValue::Int(v));},"title"=>if let Some(v)=title(t){e.insert(k.to_string(),EntityValue::Text(v));},"description"=>if let Some(v)=description(t){e.insert(k.to_string(),EntityValue::Text(v));},_=>{}}}e}
#[cfg(test)]mod tests{use super::*;#[test]fn deadline(){let e=extract_entities("Please add a deadline for HDL tomorrow at 6 PM titled lab report","CREATE_DEADLINE");assert_eq!(e.get("course"),Some(&EntityValue::Text("HDL".into())));assert_eq!(e.get("time"),Some(&EntityValue::Text("18:00".into())));assert_eq!(e.get("title"),Some(&EntityValue::Text("lab report".into())));}#[test]fn ids(){let e=extract_entities("remove deadline 7","DELETE_DEADLINE");assert_eq!(e.get("deadline_id"),Some(&EntityValue::Int(7)));}}
