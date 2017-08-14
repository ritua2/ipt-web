#include "rose.h"
#include "Data.h"
#include <list>
#include <string>
#include <list>
#include <vector>
#include <regex.h>
using namespace std;
using namespace SageBuilder;
using namespace SageInterface;
void functionAnalysis(SgForStatement*);
void arrayFor(SgBasicBlock*,SgForStatement*,int,char*);
SgStatement* userFileChoice( Rose_STL_Container<SgStatement*> ,int*);
string replaceString(string , string , string);
string translateCuda(SgForStatement* ,string ,string ,int);
bool nestedLoops(SgBasicBlock*);
bool find( Rose_STL_Container<SgNode*>, const char*);
void insertHeaders(SgGlobal*);
void writeToFile(SgStatement*);
void insertHeaders_stencil(SgGlobal*);
void getVars(SgBasicBlock*);
void getPointers(SgBasicBlock*);
void stencil_generalOps(SgBasicBlock*,string,string,SgStatement*);
SgStatement* variableDeclarations_stencil(SgBasicBlock*, SgForStatement*,int);
void buildMPIFunctions(SgBasicBlock*, SgForStatement*);
void CUDATranslations();
void replaceVariable(SgStatement*, SgScopeStatement*);
void insertExchange(char*[],SgBasicBlock*);
void generalMPI(SgBasicBlock*);
void variableDeclarations_MPI(SgBasicBlock*, SgForStatement*,int);
void setForLoopBounds_MPI(SgForStatement*,int);
void upperAndLowerLimitValues_MPI(SgExpression*,SgExpression*,SgForStatement*,int);
char* variableDeclarations_OpenMP(SgBasicBlock* , SgForStatement*);
void insertPragmas(SgForStatement*, SgBasicBlock*,char*,bool,bool);
void insertOffload( SgBasicBlock*,char*);
SgStatement* insertSplitOp( char*[],SgBasicBlock*);
SgStatement* insertCollectOp( char*[],SgBasicBlock*);
void insertReduceOp(int);
SgBasicBlock* getFunction();
string plus1(string, string);
string Array;
SgNode* getForStatement(SgBasicBlock*,SgProject*);
Rose_STL_Container<SgNode*> funcListCreated;
Rose_STL_Container<SgName> completeList;
char var[25]= "rose_";
std::string name;
int which_language =0;
int numTimes = 0;
int main( int argc, char* argv[]){
  char* part = (char*)malloc(256);
  if(SgProject :: get_verbose() > 0)
    printf("//In prePostTraversal.C : main() \n");
  SgProject* project = frontend(argc,argv);
  ROSE_ASSERT (project != NULL);
  SgGlobal* globalscope = getFirstGlobalScope(project);
  SgFunctionDeclaration* mainFunc = findMain(project);
  SgBasicBlock* body= mainFunc->get_definition()->get_body();
  pushScopeStack(globalscope);
  printf("\nNOTE: We currently support only C and C++ programs.\n");
  printf("Please enter which type of parallel program you want to create.  Type 1 for MPI, 2 for OpenMP or 3 for Cuda. \n");
  cin>>which_language;
  printf("\nPlease note that the default setting for the initialization function is set to main.\n");
  SgBasicBlock *func_body= body;
  SgType* return_type = buildIntType();
  if (func_body != NULL)
  {
    if (func_body->get_statements().size() > 1)
    {
      SgForStatement* loop;
      SgNode* isloop;
      if(which_language==1)
      {
        SgFile * cur_file = project->get_fileList()[0];
        string orig_name = cur_file->get_file_info()->get_filenameString();
        string file_suffix = StringUtility::fileNameSuffix(orig_name);
        orig_name = StringUtility::stripPathFromFileName(orig_name);
        string naked_name = StringUtility::stripFileSuffixFromFileName(orig_name);
        cur_file->set_unparse_output_filename("rose_"+naked_name+"_MPI."+file_suffix);
        
        int iteration_count = 0;
        generalMPI(func_body);//build the mpi init size rank and finalize methods
        buildMPIFunctions(func_body,loop);
        int  main_pattern;
        char both;
        bool mult = true;
        printf("\nWhich of the following patterns whould you like. \n1. Single For-Loop Parallelization \n2. Nested For-Loop Parallelization \n3. Stencil \n4. Pipeline \n5. Data Distribution and Data Collection \n6. Data Distribution \n7. Data Collection. \n");
        cin>>main_pattern;
        int count =0;
        while(mult){//multiple for loops check
          if(main_pattern ==6)
            insertSplitOp(argv,body);
          else if(main_pattern ==7)
          {
            int collection_type;
            printf("\nWould you like to do the data collection of a \n1. Variable  \n2. Array? \n");
            cin >> collection_type;
            if(collection_type ==1){variableDeclarations_stencil(func_body,loop,count);}
            else insertReduceOp(count);
          }
          else if(main_pattern ==5){
            insertSplitOp(argv,body);
            int collection_type;
            printf("\nWould you like to do the data collection of a \n1. Variable  \n2. Array? \n");
            cin >> collection_type;
            if(collection_type ==1){insertReduceOp(count);}//do reduce allreduce without for loop?
            else insertSplitOp(argv,func_body);
            
          }
          else if(main_pattern ==3&& iteration_count ==0)
          {
            printf("\nNOTE: Currently supported stencil operations are with 1 dimensional and 2 dimensional matrices.\n");
            printf("\nThe stencil pattern can be used with or without for loop paralellization.  Would you like to parallelize the loop as well?(Y/N) ");
            cin >> both;
            insertHeaders_stencil(globalscope);
            //stencil_generalOps(func_body);
          }
          iteration_count ++;
          if(main_pattern==1 ||main_pattern ==2|| both =='y' || both =='Y')
          {//for loop parallelization code
            printf("\nPlease enter the name of the function that you wish to parallelize.\n");
            func_body = getFunction();
            generalMPI(func_body);
            isloop = getForStatement(func_body,project);
            loop = isSgForStatement(isloop);
            SgStatement* upper = getLoopCondition(loop);
            SgStatementPtrList& initStatements = loop->get_init_stmt();
            SgStatement* lower = initStatements.front();
            SgExpression* upperbound =isSgBinaryOp(isSgExprStatement(upper)->get_expression())->get_rhs_operand_i();
            SgExpression* lowerbound =isSgExprStatement(lower)->get_expression();
            SgAssignOp* assign = isSgAssignOp(lowerbound);
            //if(loop==NULL||assign->get_rhs_operand()==NULL)printf("\n\n\n\n\n");
            upperAndLowerLimitValues_MPI(upperbound,assign->get_rhs_operand(),loop,count);
            setForLoopBounds_MPI(loop,count);
            //data collection code
            int collection_type;
            printf("\nWould you like to do the data collection of a \n1. Variable\n 2. Array. \n");
            cin >> collection_type;
            if(collection_type ==2){
              printf("Please enter the function in which data collection is to occur. \n");
              SgBasicBlock* function = getFunction();
              printf("Please enter the name of the array to reduce. Possible arrays are:\n");
              getPointers(function);  
              char* array_name = (char*)malloc(256);
              cin >>   array_name;
              arrayFor(function,loop,count,array_name);       
              
            }
            else if (collection_type ==1 && main_pattern ==2)
            {
              variableDeclarations_stencil(func_body,loop,count);
              insertExchange(argv,func_body);
            }
            else {
              variableDeclarations_MPI(func_body,loop,count);
            }
          }
          if(main_pattern ==3 && (both =='N' || both =='n'))
          {
            int pattern,collection_type,line;
            SgStatement* start;
            SgStatement* end;
            printf("\nNOTE: Data Distributions is categorized as breaking a matrix into smaller matrices.  As such we will prompt for exchange operation regardless of chosen prompt.\n");
            printf("\nWould you like to do this pattern with \n1. data collection  \n2. Data collection and distribution  \n3. Neither data collection or distribution \n4. Data Distribution. \n");
            cin >> pattern;
            if(pattern==2||pattern ==4)
            {
              printf("\nNOTE: For an array to be distributed properly, it must distributed evenly across all processes.  As such, please make sure that your number of array entries is divisible by the number of processes you are using.\n");
              start = insertSplitOp(argv,func_body);
            }
            
            if(pattern !=3||pattern!=4)
            {
              printf("\nWould you like to do the data collection of a \n1. Variable\n 2. Array? \n");
              cin >> collection_type;
              if(collection_type ==2){
                end = insertCollectOp(argv,func_body);
              }
              else if (collection_type ==1)
              {
                end = variableDeclarations_stencil(func_body,loop,count);
              }
              
              if(pattern ==2)
              {
                //replace variables
                while(start !=end)
                {
                  replaceVariable(start,start->get_scope());
                  start = getNextStatement(start);
                }
                
              }
              
            }
            insertExchange(argv,func_body);
          }
          
          
          cout << "Would you like to do this MPI pattern again?(Y/N) "<<endl;
          char input;
          cin >> input;
          if(input == 'N'||input =='n')
            mult = false;
          else {
            printf("\nPlease enter the name of the function that you wish to parallelize. \n");
            func_body = getFunction();
            loop = isSgForStatement(getForStatement(func_body,project));
            count++;
          }
          
        }
        printf("\nAre you writing anything?(Y/N) \n");
        char input;
        cin >> input;
        if(input =='y'||input =='Y')
        {
          printf("\nWould you like \n1. one process to do writing\n2.multiple processes to do the writing?\n");
          int numProcesses;
          cin >> numProcesses;
          if(numProcesses ==1)
          {
            char more = 'y';
            printf("\nNOTE: To make sure that one process is writing to the data, we will need to know at which lines you are writing data. \n");
            while(more == 'y' || more =='Y'){
              int pos;
              //                                              SgStatement* write = userFileChoice(func_body->get_statements(),&pos);
              writeToFile(*(func_body->get_statements().begin()));
              int number;
              printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert a line number where you are writing data.\n");
              cin >>number;
              SgStatement* exc = (*(func_body->get_statements().begin()));
              int i ;
              for ( i = 1; i<number;i++){
                exc = getNextStatement(exc);
              }
              
              attachArbitraryText(exc,"if(rose_rank==0)",PreprocessingInfo::before);
              printf("\nDo you have any other data output calls?(Y/N) \n");
              cin >> more;
            }
          }
        }
        insertHeaders(globalscope);
      }                                                                                                                                                                                                                                                                
      else if (which_language ==2)
      {
        SgFile * cur_file = project->get_fileList()[0];
        string orig_name = cur_file->get_file_info()->get_filenameString();
        string file_suffix = StringUtility::fileNameSuffix(orig_name);
        orig_name = StringUtility::stripPathFromFileName(orig_name);
        string naked_name = StringUtility::stripFileSuffixFromFileName(orig_name);
        
        cur_file->set_unparse_output_filename("rose_"+naked_name+"_OpenMP."+file_suffix);
        char offload;
        bool offloadMode = false;
        bool forlooppara = false;
        char forlooppar;
        cout<< "Would you like this program to be in offload mode?(Y/N) "<<endl;
        cin >>offload;
        
        cout<< "Would you like to parallelize a for loop?(Y/N) "<<endl;
        cin >> forlooppar;
        if(forlooppar == 'y' || forlooppar == 'Y')
          forlooppara = true;
        bool again = true;
        while(again){
          printf("\nPlease enter the function in which you wish to insert a pragma(function to parallelize). \n");
          func_body = getFunction();
          SgExpression* forTest;
          if(offload =='Y'||offload =='y')
          {
            offloadMode = true;
            cur_file->set_unparse_output_filename("rose_"+naked_name+"_OpenMP_Offload."+file_suffix);
          }
          if(!(!forlooppara && offloadMode)){
            isloop = getForStatement(func_body,project);
            loop = isSgForStatement(isloop);
            forTest = loop->get_test_expr();
          }
          if(offloadMode)
            insertHeader("offload.h",PreprocessingInfo::before,true,globalscope);
          if(forlooppara)
            insertPragmas(loop,func_body,part,offloadMode,forlooppara);
          else insertOffload(func_body,part);
          if(!(!forlooppara && offloadMode) && strstr(isSgNode(forTest)->unparseToString().c_str(),"&")!=NULL){
            Rose_STL_Container<SgNode*> loopExpressions = NodeQuery::querySubTree(loop->get_test_expr(),V_SgExpression);
            Rose_STL_Container<SgNode*> ::iterator i = loopExpressions.begin()+2;
            SgTreeCopy copyHelp;
            SgExpression* forLoopExp;
            forLoopExp = isSgExpression(isSgExpression(*(i-1))->copy(copyHelp));
            
            while(i!= loopExpressions.end())
            {
              if(strstr(isSgNode(*i)->unparseToString().c_str(),")"))
              {
                attachArbitraryText(loop->get_loop_body(),"if("+isSgNode(*i)->unparseToString()+")",PreprocessingInfo::before);
                break;
              }
              i++;
            }
            replaceExpression(isSgExpression(*(loopExpressions.begin())),forLoopExp);
            cout<< isSgNode(loop->get_test_expr())->unparseToString()<<endl;
          }
          
          printf("\nWould you like to parallelize another loop?(Y/N)\n");
          char c;
          cin >>c;
          if(c == 'n' || c =='N')
            again = false;
        }
        
        insertHeaders(globalscope);
      }
      else if (which_language ==3)
      {
        //insert CUDA code
        
        CUDATranslations();
        SgFile * cur_file = project->get_fileList()[0];
        string orig_name = cur_file->get_file_info()->get_filenameString();
        string file_suffix = StringUtility::fileNameSuffix(orig_name);
        orig_name = StringUtility::stripPathFromFileName(orig_name);
        string naked_name = StringUtility::stripFileSuffixFromFileName(orig_name);
        cur_file->set_unparse_output_filename("rose_"+naked_name+".cu");
        //CUDATranslations();
      }
    }
  }
  printf("\nRunning Consistency Tests\n");
  AstTests :: runAllTests (project);
  return backend(project);
}
void insertOffload(SgBasicBlock* func_body,char* part){
  pushScopeStack(func_body);
  Rose_STL_Container<SgNode*> Input;
  Rose_STL_Container<SgNode*> Output;
  Rose_STL_Container<SgNode*> InOut;
  Rose_STL_Container<SgNode*> functions; //  NodeQuery::querySubTree(loop,V_SgFunctionCallExp);
  Rose_STL_Container<SgNode*> varList; // NodeQuery::querySubTree(loop,V_SgVarRefExp);
  Rose_STL_Container<SgNode*>::iterator j = functions.begin();
  int answer;
  writeToFile(getFirstStatement(func_body));
  int ending;
  int begin;
  SgStatement* header;
  int i = 1;
  printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number at which you would like to begin offload parallelization.\n");
  cin >>begin;
  printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number at which you would like to end offload parallelization.\n");
  cin >>ending;
  SgStatement* current_statement = getFirstStatement(func_body);
  while(i!=begin)
  {
    current_statement = getNextStatement(current_statement);
    i++;
  }
  header = current_statement;
  for(i = begin;i<= ending;i++)
  {
    if(isSgForStatement(current_statement)!= NULL)
    {
      printf("A for loop has been found.  Would you like to run it in parallel?(Y/N)\n");
      char choice;
      cin >> choice;
      if(choice == 'y' || choice == 'Y')
      {
        attachArbitraryText(current_statement,"#pragma omp parallel for");
      }
    }
    Rose_STL_Container<SgNode*> functions_temp =  NodeQuery::querySubTree(current_statement,V_SgFunctionCallExp);
    Rose_STL_Container<SgNode*> varList_temp = NodeQuery::querySubTree(current_statement,V_SgVarRefExp);    
    Rose_STL_Container<SgNode*> :: iterator k = functions_temp.begin();
    while(k!=functions_temp.end())
    {
      functions.push_back(*k);
      k++;
    }
    k = varList_temp.begin();
    while(k!=varList_temp.end())
    {
      varList.push_back(*k);
      k++;
    }
    current_statement = getNextStatement(current_statement);
  }
  
  j= functions.begin();
  while(j!=functions.end())
  {
    if((isSgFunctionCallExp(*j))->getAssociatedFunctionSymbol()!= NULL){
      SgFunctionSymbol* sym = (isSgFunctionCallExp(*j))->getAssociatedFunctionSymbol();
      if(sym->get_declaration () != NULL){    
        SgFunctionDeclaration* decl =(isSgFunctionCallExp(*j))->getAssociatedFunctionSymbol()->get_declaration ();
        if(decl != NULL){
          cout <<isSgNode(decl)->unparseToString()<<endl;
          attachArbitraryText(decl,"__declspec(target(mic))");
        }}}
    j++;
  }
  
  j = varList.begin();
  while(j!= varList.end())
  {
    if(find(Input,(*j)->unparseToString().c_str())&&find(Output,(*j)->unparseToString().c_str())&&find(InOut,(*j)->unparseToString().c_str()))
    {
      
      cout << "\nDo you want "<< (*j)->unparseToString().c_str()<<" to be added to \n1. Input \n2. Output \n3. Input/Output \n4. None?"<<endl;
      cin >>answer;
      switch(answer){
      case 1: Input.push_back(isSgNode(*j));break;
      case 2: Output.push_back(isSgNode(*j));break;
      case 3: InOut.push_back(isSgNode(*j));break;
      default:break;
      }
    }
    j++;
  }
  string str1 = "offload target (mic) ";
  j = Input.begin();
  Rose_STL_Container<SgNode*> arrays;
  Rose_STL_Container<SgNode*> variables;
  while(j != Input.end())
  {
    if(lookupNamedTypeInParentScopes((*j)->unparseToString())->containsInternalTypes())
    {
      arrays.push_back(*j);
    }
    else{
      variables.push_back(*j);
    }
    
    j++;
  }
  j = variables.begin();
  if(j!= variables.end())
    str1.append(" in(");
  
  while(j!= variables.end())
  {
    str1.append((*j)->unparseToString().c_str());
    if((j+1)!=variables.end())
      str1.append(",");
    else str1.append(") ");
    j++;
  }
  
  j = arrays.begin();
  while(j!=arrays.end()){
    printf("What is the length of the array ");
    cout <<(*j)->unparseToString()<<endl;
    string length;
    cin >> length;
    str1.append("in( "+(*j)->unparseToString()+":length("+length+")) ");
    j++;
  }
  j = Output.begin();
  arrays.clear();
  variables.clear();
  while(j != Output.end())
  {
    if(lookupNamedTypeInParentScopes((*j)->unparseToString())->containsInternalTypes())
    {
      arrays.push_back(*j);
    }
    else{
      variables.push_back(*j);
    }
    
    j++;
  }
  j = variables.begin();
  if(j!= variables.end())
    str1.append(" out(");
  
  while(j!= variables.end())
  {
    str1.append((*j)->unparseToString().c_str());
    if((j+1)!=variables.end())
      str1.append(",");
    else str1.append(") ");
    j++;
  }
  
  j = arrays.begin();
  while(j!=arrays.end()){
    printf("What is the length of the array ");
    cout <<(*j)->unparseToString()<<endl;
    string length;
    cin >> length;
    str1.append("out( "+(*j)->unparseToString()+":length("+length+")) ");
    j++;
  }
  j = InOut.begin();
  arrays.clear();
  variables.clear();
  while(j != InOut.end())
  {
    if(lookupNamedTypeInParentScopes((*j)->unparseToString())->containsInternalTypes())
    {
      arrays.push_back(*j);
    }
    else{
      variables.push_back(*j);
    }
    
    j++;
  }
  j = variables.begin();
  if(j!= variables.end())
    str1.append(" inout(");
  
  while(j!= variables.end())
  {
    str1.append((*j)->unparseToString().c_str());
    if((j+1)!=variables.end())
      str1.append(",");
    else str1.append(") ");
    j++;
  }
  
  j = arrays.begin();
  while(j!=arrays.end()){
    printf("What is the length of the array ");
    cout <<(*j)->unparseToString()<<endl;
    string length;
    cin >> length;
    str1.append("inout( "+(*j)->unparseToString()+":length("+length+")) ");
    j++;
  }
  
  string* vprag = new string(str1);
  SgPragmaDeclaration* varPragma = buildPragmaDeclaration(*vprag);
  insertStatementBefore(header,varPragma);
  attachArbitraryText(header,"{");
  attachArbitraryText((current_statement),"}");
  popScopeStack();
}
void replaceVariable(SgStatement* check, SgScopeStatement* body){
  Rose_STL_Container<SgNode*> addOps= NodeQuery::querySubTree(check,V_SgExpression);
  if (addOps.size()!=0){
    int i;
    for(i = 0; i< addOps.size();i++){//for each expression
      SgExpression* add_op = isSgExpression(addOps[i]);
      
      if (strcmp(isSgNode(add_op)->unparseToString().c_str(),Array.c_str()) == 0){//check if it equals replacevar
        string tempVar = "temp_"+Array;
        if(lookupSymbolInParentScopes(tempVar.c_str(),body)==NULL){
          SgVariableDeclaration* declaration = buildVariableDeclaration(tempVar.c_str(),add_op->get_type());
          prependStatement(declaration,body);
          // printf("creating variable\n\n");
        }
        SgExpression* myExp = buildOpaqueVarRefExp(tempVar.c_str(),findMain(getProject())->get_definition()->get_body());
        SgNode* result = SageInterface::replaceWithPattern(add_op, myExp);
        
      }
    }
  }
  
}
void writeToFile(SgStatement* body){
  int count=1;
  FILE* qFile = fopen("numberedCode.C","w");
  if (qFile == NULL) printf ("Error opening file");
  else{
    char* line = NULL;
    SgStatement* stmt = (body);
    while(getNextStatement(stmt)!=NULL){
      fprintf(qFile,"%d %s\n",count,isSgNode((stmt))->unparseToString().c_str());
      stmt = getNextStatement(stmt);
      count++;
    }
    fprintf(qFile,"%d %s\n",count,isSgNode((stmt))->unparseToString().c_str());
  }fclose(qFile);
  
}
SgStatement* userFileChoice( Rose_STL_Container<SgStatement*> body,int* position){
  writeToFile(*body.begin());
  int number,pos;
  printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number at which you would like the statement.\n");
  cin >>number;
  printf("\nWould you like the statement\n1. before\n2. after\n3. in the statement\n");
  cin >> pos;
  SgStatement* exc = ((*body.begin()));
  int i ;
  for ( i = 1; i<number;i++){
    exc = getNextStatement(exc);
  }
  if (pos == 3)
  {
    Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(exc,V_SgStatement);
    Rose_STL_Container<SgStatement*> :: iterator j ;
    Rose_STL_Container<SgStatement*> list =getScope(isSgStatement(*(varList.end()-1)))->getStatementList();
    j = list.begin();
    return userFileChoice(list,position);
  }
  *position = pos;
  return exc;
}
SgStatement* insertSplitOp( char* argv[],SgBasicBlock* body){
  string array1,array2;
  string arrayType;
  string rows,cols;
  int number;
  int pos;
  printf("\nPlease enter the name of the function in which you wish to distribute the data. \n");
  body = getFunction();
  if(numTimes ==0){
    SgVariableDeclaration* variableDeclaration = buildVariableDeclaration("tempM_fraspa",buildIntType());
    prependStatement(variableDeclaration,body);
    variableDeclaration = buildVariableDeclaration("tempN_fraspa",buildIntType());
    prependStatement(variableDeclaration,body);
  }
  
  pushScopeStack(body);
  writeToFile(getFirstStatement(body));
  printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number that will serve as a hook for the placement of the data distribution. \n");
  cin >>number;
  printf("\nWould you like the statement\n1. before\n2. after\n3. in the statement\n");
  
  cin >> pos;
  SgStatement* exc = (getFirstStatement(body));
  int i = 0;
  for ( i = 1; i<number;i++){
    exc = getNextStatement(exc);
  }
  if(pos ==2)
    exc = getNextStatement(exc);
  else if (pos==3)
  {
    Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(exc,V_SgStatement);
    Rose_STL_Container<SgStatement*> :: iterator j ;
    Rose_STL_Container<SgStatement*> list =getScope(isSgStatement(*(varList.end()-1)))->getStatementList();
    //printf("%s",isSgNode(*(varList.end()-1))->unparseToString().c_str());
    j = list.begin();
    exc = userFileChoice(list,&pos);
  }
  printf("\nPlease enter either a constant or the variable containing the number of rows. \n");
  cin>>rows;
  printf("\nPlease enter either a constant or the variable containing the number of cols.\n");
  cin>>cols;
  printf("\nPlease enter the name of the array to be split. Possible arrays are : ");
  getPointers(body);
  cin>>array1;
  array2 = "temp_"+array1;
  Array = array1;
  SgVariableDeclaration* variableDeclaration = buildVariableDeclaration(array2,lookupNamedTypeInParentScopes(Array,body));
  prependStatement(variableDeclaration,body);
  string varType(isSgNode(lookupNamedTypeInParentScopes(Array,body))->unparseToString().c_str());
  varType.erase(varType.find_first_of('*',0),varType.size());
  cout << varType<<endl;
  
  arrayType = varType;
  stencil_generalOps(body,rows,cols,exc);
  char in[21];
  sprintf(in,"%d",numTimes);
  string test(in);
  attachArbitraryText(exc,array2+"=allocMatrix<"+arrayType+">("+array2+","+rows+","+cols+");",PreprocessingInfo::before);
  
  attachArbitraryText(exc,array2+" = split<"+arrayType+">("+array1+","+array2+",tempM_fraspa,tempN_fraspa,P"+test+",Q"+test+",p"+test+",q"+test+",rowcomm,colcomm);",PreprocessingInfo::before);
  attachArbitraryText(exc,array2+" = exchange<"+arrayType+">("+array2+","+rows+"+2,"+cols+"+2,P"+test+",Q"+test+",p"+test+",q"+test+",comm2d, rowcomm, colcomm, diag1comm, diag2comm);",PreprocessingInfo::before);
  printf("\nPlease note that for array distribution we automatically insert an exchange statement right after the split statement.\n");
  popScopeStack();
  return exc;
}
SgStatement* insertCollectOp( char* argv[],SgBasicBlock* body)
{
  string array1,array2;
  string arrayType;
  string rows,cols;
  int number;
  int pos;
  printf("Please enter the name of the function in which you wish to collect the data. ");
  body = getFunction();
  pushScopeStack(body);
  writeToFile(getFirstStatement(body));
  printf("For your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number that will serve as the hook for the corresponding collect statement. ");
  cin >>number;
  printf("Would you like the statement\n1. before\n2. after\n3. in the statement\n");
  cin >> pos;
  SgStatement* exc = (getFirstStatement(body));
  int i = 0;
  for ( i = 1; i<number;i++){
    exc = getNextStatement(exc);
  }
  if(pos ==2)
    exc = getNextStatement(exc);
  else if (pos==3)
  {
    Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(exc,V_SgStatement);
    Rose_STL_Container<SgStatement*> :: iterator j ;
    Rose_STL_Container<SgStatement*> list =getScope(isSgStatement(*(varList.end()-1)))->getStatementList();
    //                printf("%s",isSgNode(*(varList.end()-1))->unparseToString().c_str());
    j = list.begin();
    exc = userFileChoice(list,&pos);
  }
  printf("\nPlease enter either a constant or the variable containing the number of rows. \n");
  cin>>rows;
  printf("\nPlease enter either a constant or the variable containing the number of cols.\n");
  cin>>cols;
  printf("\nPlease enter the name of the array to be collected. Possible arrays are \n");
  getPointers(body);
  cin>>array1;
  string varType(isSgNode(lookupNamedTypeInParentScopes(array1,body))->unparseToString().c_str());
  varType.erase(varType.find_first_of('*',0),varType.size());
  cout << varType<<endl;
  
  stencil_generalOps(body,rows,cols,exc);
  char in[21];
  sprintf(in,"%d",numTimes);
  string test(in);
  if(Array.empty()){
    printf("\nPlease enter the name of the array to store it in. \n");
    cin>>array2;
  }
  else
  {
    attachArbitraryText(exc,rows +"=tempM_fraspa;",PreprocessingInfo::before);
    attachArbitraryText(exc,cols+"=tempN_fraspa;",PreprocessingInfo::before);
    array2 = "temp_"+array1;
    SgVariableDeclaration* declaration = buildVariableDeclaration(array2.c_str(),lookupNamedTypeInParentScopes(array1,body));//create
    prependStatement(declaration,body);
    attachArbitraryText(exc,array2+"=allocMatrix<"+arrayType+">("+array2+","+rows+","+cols+");",PreprocessingInfo::before);//allocate
  }
  attachArbitraryText(exc,array2+" = collect<"+arrayType+">("+array1+","+array2+","+rows+","+cols+",P"+test+",Q"+test+",p"+test+",q"+test+",rowcomm,colcomm);",PreprocessingInfo::before);
  if(!Array.empty()){
    SgExprStatement* funcCall = buildFunctionCallStmt("free",buildVoidType(),buildExprListExp(buildVarRefExp(array1,body)),body);
    insertStatement((exc),funcCall);
    attachArbitraryText(exc,array1+"=allocMatrix<"+arrayType+">("+array1+","+rows+","+cols+");",PreprocessingInfo::before);//allocate
    
    //               funcCall = buildFunctionCallStmt("memcpy",buildVoidType(),buildExprListExp(buildVarRefExp(array1,body),buildVarRefExp(array2,body),buildFunctionCallExp("sizeof",buildIntType(),buildExprListExp(buildVarRefExp(array2,body)),body)),body);
    //              insertStatement((exc),funcCall);
    
    SgForStatement* outer;
    SgForStatement* inner;
    if(lookupSymbolInParentScopes("i_fraspa",body)==NULL)
    {
      //create loop variables
      SgVariableDeclaration* declaration = buildVariableDeclaration("i_fraspa",buildIntType());
      prependStatement(declaration,body);
    }
    if(lookupSymbolInParentScopes("j_fraspa",body)==NULL){
      SgVariableDeclaration* declaration = buildVariableDeclaration("j_fraspa",buildIntType());
      prependStatement(declaration,body);
    }
    SgStatement* initializer = buildAssignStatement(buildVarRefExp("j_fraspa",body),buildIntVal(1));
    SgStatement* test = buildExprStatement(buildLessThanOp(buildVarRefExp("j_fraspa",body),buildAddOp(buildVarRefExp(rows,body),buildIntVal(1))));
    SgExpression* increment = buildAssignOp(buildVarRefExp("j_fraspa",body),buildAddOp(buildVarRefExp("j_fraspa",body),buildIntVal(1)));
    //SgStatement* bodyl = buildAssignStatement(buildPntrArrRefExp(array2+"[i][j]"),buildPntrArrRefExp(array1+"[i][j]"));
    inner = buildForStatement(initializer,test,increment,buildBasicBlock());
    attachArbitraryText(inner->get_loop_body(),array1+"[i_fraspa][j_fraspa] = "+array2+"[i_fraspa][j_fraspa];",PreprocessingInfo::inside);
    initializer = buildAssignStatement(buildVarRefExp("i_fraspa",body),buildIntVal(1));
    test = buildExprStatement(buildLessThanOp(buildVarRefExp("i_fraspa",body),buildAddOp(buildVarRefExp(rows,body),buildIntVal(1))));
    increment = buildAssignOp(buildVarRefExp("i_fraspa",body),buildAddOp(buildVarRefExp("i_fraspa",body),buildIntVal(1)));
    outer = buildForStatement(initializer,test,increment,inner);
    insertStatement(exc,outer);
    funcCall = buildFunctionCallStmt("free",buildVoidType(),buildExprListExp(buildVarRefExp(array2,body)),body);
    insertStatement((exc),funcCall);
    string tempVar = "temp_"+Array;
    if(lookupSymbolInParentScopes(tempVar.c_str())==NULL){
      SgVariableDeclaration* declaration = buildVariableDeclaration(tempVar.c_str(),lookupNamedTypeInParentScopes(Array,body));
      prependStatement(declaration,body);
    }
    
    
    funcCall = buildFunctionCallStmt("free",buildVoidType(),buildExprListExp(buildVarRefExp("temp_"+Array)));
    insertStatement((exc),funcCall);
    
  }
  popScopeStack();
  return exc;
}
void insertExchange( char* argv[],SgBasicBlock* body){
  int number;
  char check;
  bool exchange = false;
  int pos = 0;
  PreprocessingInfo::RelativePositionType loc;
  printf("\nDo you want an exchange statement?(Y/N) \n");
  cin >> check;
  if(check =='y' || check =='Y')
    exchange = true;
  while (exchange){
    printf("\nPlease enter the name of the function in which you wish to insert an exchange statement.\n");
    body = getFunction();
    pushScopeStack(body);
    writeToFile(getFirstStatement(body));
    
    printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number at which you would like the exchange statement. \n");
    cin >> number;
    printf("\nWould you like the statement\n 1. before\n 2. after\n3. in the statement\n");
    cin >> pos;
    SgStatement* exc = (getFirstStatement(body));
    int i = 0;
    for ( i = 1; i<number;i++){
      exc = getNextStatement(exc);
      //              cout<<"Statement  "<<i<<" is "<<isSgNode(exc)->unparseToString().c_str()<<endl;
      
    }
    if (pos==3)
    {
      //write to file and ask user again this time with loop body
      Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(exc,V_SgStatement);
      Rose_STL_Container<SgStatement*> :: iterator j ;
      Rose_STL_Container<SgStatement*> list =getScope(isSgStatement(*(varList.end()-1)))->getStatementList();
      j = list.begin();
      exc = userFileChoice(list,&pos);
    }
    string rows;
    printf("\nPlease enter the variable containing the number of rows. \n");
    cin>>rows;
    string cols;
    printf("\nPlease enter the variable containing the number of cols. \n");
    cin>>cols;
    string array;
    string arrayType;
    printf("\nPlease enter the array name. Possible arrays are : \n");
    getPointers(body);
    cin>>array;
    string varType(isSgNode(lookupNamedTypeInParentScopes(array,body))->unparseToString().c_str());
    varType.erase(varType.find_first_of('*',0),varType.size());
    arrayType = varType;
    if(lookupVariableSymbolInParentScopes("tempM_fraspa") ==NULL){
      SgVariableDeclaration* variableDeclaration = buildVariableDeclaration("tempM_fraspa",buildIntType());
      prependStatement(variableDeclaration,body);
      variableDeclaration = buildVariableDeclaration("tempN_fraspa",buildIntType());
      prependStatement(variableDeclaration,body);
    }
    if(pos ==1)
    {
      loc =PreprocessingInfo::before;
    }
    else loc = PreprocessingInfo::after;
    stencil_generalOps(body,rows,cols,exc);
    char in[21];
    sprintf(in,"%d",numTimes);
    string test(in);
    attachArbitraryText(exc,array+" = exchange<"+arrayType+">("+array+","+rows+"+2,"+cols+"+2,P"+test+",Q"+test+",p"+test+",q"+test+",comm2d, rowcomm, colcomm, diag1comm, diag2comm);",loc);
    printf ("Do you have any other lines before which you would like to insert an exchange statement?(Y/N) ");
    cin >>check;
    if(check == 'n'||check =='N')
      exchange = false;
    popScopeStack();
  }
}
bool nestedLoops(SgBasicBlock* loop_body){
  Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(loop_body,V_SgForStatement);
  if(varList.empty())
    return false;
  else return true;
}
void functionAnalysis(SgForStatement* loop)
{
  
  Rose_STL_Container<SgNode*> funcList = NodeQuery::querySubTree(loop,V_SgFunctionCallExp);
  Rose_STL_Container<SgNode*> :: iterator k = funcList.begin();
  
  bool check = true;
  
  Rose_STL_Container<SgName> :: iterator m = completeList.begin();
  
  k = funcList.begin();
  while(k != funcList.end()){
    SgFunctionCallExp* currentFunction = isSgFunctionCallExp(*k);
    SgFunctionDeclaration* currentDeclaration = findFunctionDeclaration(getProject(),currentFunction->getAssociatedFunctionSymbol()->get_name().getString(),NULL,true);
    if(find(funcListCreated,isSgNode(currentDeclaration)->unparseToString().c_str())){
      completeList.push_back(currentFunction->getAssociatedFunctionSymbol()->get_name());
      funcListCreated.push_back(isSgNode(currentDeclaration));
      //add to local array static
      Rose_STL_Container<SgNode*> funcListsub= NodeQuery::querySubTree(currentDeclaration->get_definition()->get_body(),V_SgFunctionCallExp);                         
      Rose_STL_Container<SgNode*> :: iterator m = funcListsub.begin();
      while(m!=funcListsub.end())
      {
        funcList.push_back(*m);
        m++;
      }
      k = funcList.begin();
      
    }
    k++;
    
  }
  m = completeList.begin();
  while(m!=completeList.end())
  {
    cout<<( *m).str()<<endl;
    SgFunctionDeclaration* currentDeclaration = findFunctionDeclaration(getProject(),(*m).getString(),NULL,true);
    string test = isSgNode(currentDeclaration)->unparseToString().c_str();
    Rose_STL_Container<SgName> :: iterator n = completeList.begin();
    test = "__device__ " + test;
    while(n!=completeList.end()){
      int pos = test.find((*n).getString()+"(");
      // printf("%d\n",pos);
      while(pos!=-1){ 
        string checker = "abcdefghijklmnopqrstuvwxyz0123456789";
        if(checker.find(test.at(pos-1))==-1)
          test= test.substr(0,pos+(*n).getString().length())+"_rose"+test.substr(pos+(*n).getString().length());
        
        pos = test.find((*n).getString()+"(",pos+1);                        
      }
      n++;        
    }
    attachArbitraryText(getFirstGlobalScope(getProject()),test);
    
    m++;
  }
}
void CUDATranslations(){
  char temp;
  std::string lines;
  std::string functionVariables;
  printf("\nPlease enter the function in which you wish to insert the kernel call(parallelize the for loop). \n");
  SgBasicBlock* func_body = getFunction();
  printf("\nWould you like \n1. Single for Loop Parallelization \n2. Nested for Loop Parallelization?\n ");
  int type;
  cin >> type;
  SgNode* isloop = getForStatement(func_body,getProject());
  //  Functional analysis
  functionAnalysis(isSgForStatement(isloop));
  std::string rows;
  std::string cols;
  if(type == 1 )
    rows = "1";
  else{
    cout <<endl<< "Please enter the number of rows in the array to be calculated?   Either hardcoded values or variable name that contains the number of rows is acceptable." <<endl;
    cin >>rows;
  }
  cout <<endl<< "Please enter the number of columns in the array to be calculated?  Either hardcoded values or variable name that contains the number of rows is acceptable." <<endl;
  cin >>cols;
  
  //get list of device variables to be stored 
  Rose_STL_Container<SgNode*> vars;
  Rose_STL_Container<SgNode*> deviceVars;
  Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(isSgForStatement(isloop),V_SgVarRefExp);
  Rose_STL_Container<SgNode*> loopList = NodeQuery::querySubTree(isSgForStatement(isloop),V_SgForStatement);
  Rose_STL_Container<SgNode*> :: iterator j = varList.begin();
  Rose_STL_Container<SgNode*> :: iterator k = loopList.begin();
  while(j!= varList.end()){
    if(find(vars,(*j)->unparseToString().c_str()) && find(deviceVars,(*j)->unparseToString().c_str())){                     
      if(lookupNamedTypeInParentScopes((*j)->unparseToString().c_str(),func_body)->containsInternalTypes())
        deviceVars.push_back(*j);
      else if(strcmp(getLoopIndexVariable(isloop)->get_name().str(),(*j)->unparseToString().c_str())!=0)
        if(type !=2 || (type ==2 && strcmp(getLoopIndexVariable(*(k+1))->get_name().str(),(*j)->unparseToString().c_str())!=0)) 
        {
          //cout <<getLoopIndexVariable(*(k+1))->get_name().str();
          vars.push_back(*j);
        }
    }
    j++;            
  }
  
  /*
  *       Add device variable declarations 
  *       If Arrays create a device array otherwise add it to the list of variables
  */
  SgForStatement* loop = isSgForStatement(isloop);
  j = deviceVars.begin();
  SgVariableDeclaration* varDecl;
  while(j!=deviceVars.end()){
    if(getElementType(getElementType(lookupNamedTypeInParentScopes((*j)->unparseToString(),func_body)))!=NULL){         
      varDecl = buildVariableDeclaration("device_"+(*j)->unparseToString(),getElementType(lookupNamedTypeInParentScopes((*j)->unparseToString(),func_body)) );
    }else{ 
      varDecl = buildVariableDeclaration("device_"+(*j)->unparseToString(),lookupNamedTypeInParentScopes((*j)->unparseToString(),func_body) );
    }
    prependStatement(varDecl,func_body);    
    
    attachArbitraryText(loop,"cudaMalloc((void **) &device_"+(*j)->unparseToString() + ",( " + rows + ")*(" + cols + ")*sizeof(" + isSgNode(getElementType(lookupNamedTypeInParentScopes("device_"+(*j)->unparseToString(),func_body)))->unparseToString() + "));");
    j++;
    
  }       
  
  
  /*
  *create device and thread vars
  */
  attachArbitraryText(loop,"dim3 dimGrid("+cols+","+rows+");");
  attachArbitraryText(loop,"dim3 dimBlock(1,1);");
  
  
  /*
  *create kernel call and copy device variables 
  */
  attachArbitraryText(getNextStatement(loop),"*/");
  j = deviceVars.begin();
  string variables;
  string declaration;
  int typeVar;
  while(j!=deviceVars.end()){
    printf("\nIs the following variable 1. Input , 2. Output 3. Input/Output 4. Neither Input nor Output \n");
    cout << (*j)->unparseToString()<< "? ";
    cin >> typeVar;
    //              cout << typeVar;
    
    if(strcmp(rows.c_str(),"1")==0){
      declaration += isSgNode(lookupNamedTypeInParentScopes((*j)->unparseToString(),func_body))->unparseToString()+" "+(*j)->unparseToString()+",";
      variables += "device_"+(*j)->unparseToString()+",";
    }else{
      declaration += isSgNode(lookupNamedTypeInParentScopes("device_"+(*j)->unparseToString(),func_body))->unparseToString()+" "+(*j)->unparseToString()+",";
      variables +="device_"+ (*j)->unparseToString()+",";
    }
    
    if(typeVar == 1 || typeVar ==3)
    {
      
      if(strcmp(rows.c_str(),"1")==0){
        attachArbitraryText((loop),"cudaMemcpy("+(*j)->unparseToString()+",device_"+(*j)->unparseToString()+",("+cols+")*sizeof("+isSgNode(getElementType(lookupNamedTypeInParentScopes("device_"+(*j)->unparseToString(),func_body)))->unparseToString()+"), cudaMemcpyHostToDevice);");
        
      }
      else{
        attachArbitraryText((loop),"for(int rose_i=0; rose_i<"+rows+"; ++rose_i){cudaMemcpy(device_"+(*j)->unparseToString()+ " + rose_i*("+cols +"),"+(*j)->unparseToString()+"[rose_i],("+cols+")*sizeof("+isSgNode(getElementType(lookupNamedTypeInParentScopes("device_"+(*j)->unparseToString(),func_body)))->unparseToString()+"), cudaMemcpyHostToDevice);}");
      }
    }
    if (typeVar ==2 || typeVar ==3){
      if(getNextStatement(loop)==NULL){
        SgVariableDeclaration* temp = buildVariableDeclaration("rose_temp",buildIntType());
        insertStatementAfter(loop,temp);}
      if(strcmp(rows.c_str(),"1")==0){
        attachArbitraryText(getNextStatement(loop),"cudaMemcpy("+(*j)->unparseToString()+",device_"+(*j)->unparseToString()+",("+cols+")*sizeof("+isSgNode(getElementType(lookupNamedTypeInParentScopes("device_"+(*j)->unparseToString(),func_body)))->unparseToString()+"), cudaMemcpyDeviceToHost);");
        
      }
      else{
        attachArbitraryText(getNextStatement(loop),"for(int rose_i=0; rose_i<"+rows+"; ++rose_i){cudaMemcpy("+(*j)->unparseToString()+"[rose_i],device_"+(*j)->unparseToString()+ " + rose_i*("+cols +"),("+cols+")*sizeof("+isSgNode(getElementType(lookupNamedTypeInParentScopes("device_"+(*j)->unparseToString(),func_body)))->unparseToString()+"), cudaMemcpyDeviceToHost);}");
        
      }
      
      
    }
    
    j++;
    
  }
  j = vars.begin();
  while(j != vars.end())
  {
    //printf("\n\n%s\n\n",(*j)->unparseToString());
    //              if(strcmp((*j)->unparseToString().c_str(),rows.c_str())!=0 && strcmp((*j)->unparseToString().c_str(),cols.c_str())){
    variables +=(*j)->unparseToString()+",";
    declaration += isSgNode(lookupNamedTypeInParentScopes((*j)->unparseToString(),func_body))->unparseToString()+" "+(*j)->unparseToString()+",";
    
    j++;
  }
  
  char* test =(char*) malloc(16);
  sprintf(test,"%d",numTimes);
  
  attachArbitraryText(loop,"kernel"+string(test)+"<<<dimGrid,dimBlock>>>("+variables+rows+","+cols+");",PreprocessingInfo::before);
  
  /*
  *create kernel function
  */
  SgStatement* insertionPoint = getPreviousStatement(getFirstStatement(func_body));
  //cout << isSgNode(insertionPoint)->unparseToString();
  attachArbitraryText(insertionPoint,"void __global__ kernel"+string(test)+"("+declaration+" int device_M , int device_N){");
  attachArbitraryText(insertionPoint,"int  col   = blockIdx.x*blockDim.x;");
  attachArbitraryText(insertionPoint,"int  row = blockIdx.y*blockDim.y;");
  attachArbitraryText(insertionPoint,"int   i = row*device_N +col;");
  numTimes++;
  //need to get for loop conditions how to translate
  //attachArbitraryText(insertionPoint,"if (i < device_M*device_N && col!=0 && col!=device_N-1 && row!=0 && row !=device_M-1){");
  
  
  std::string output = translateCuda(loop,"device_M","device_N",type);
  Rose_STL_Container<SgName> :: iterator m = completeList.begin();
  while(m!=completeList.end()){
    int pos = output.find((*m)+"(");
    while(pos!=-1)
    {
      string checker = "abcdefghijklmnopqrstuvwxyz0123456789";
      if(checker.find(output.at(pos-1))==-1)
        output = output.substr(0,pos+(*m).getString().length())+"_rose"+output.substr(pos+(*m).getString().length());
      pos = output.find((*m)+"(",pos+1);
      
    }
    m++;
  }
  
  
  attachArbitraryText(insertionPoint, output);
  attachArbitraryText(insertionPoint,"}");
  attachArbitraryText(loop,"/*");
  //removeStatement(loop);
}

/*
*convert for loop into a string with the necessary change in array dimensions
*/
void replaceExpression(SgStatement* check, string replaceWith,string varToReplace){
  Rose_STL_Container<SgNode*> addOps= NodeQuery::querySubTree(check,V_SgExpression);
  if (addOps.size()!=0){
    int i;
    for(i = 0; i< addOps.size();i++){//for each expression
      SgExpression* add_op = isSgExpression(addOps[i]);
      
      if (strcmp(isSgNode(add_op)->unparseToString().c_str(),varToReplace.c_str()) == 0){//check if it equals replacevar 
        SgExpression* myExp = buildOpaqueVarRefExp(replaceWith.c_str());
        SgNode* result = SageInterface::replaceWithPattern(add_op, myExp);
        
      }
    }
  }
  
}
string replaceString(string check , string toReplace , string replaceWith){
  while(check.find(toReplace)!=string::npos){
    check.replace(check.find(toReplace),toReplace.length(),replaceWith);
    //cout << check<<endl;
  }
  return check;
  
}
string translateCuda(SgForStatement* loop,string rows,string cols, int type){
  std::string output;
  std::string initialCondition;
  std::string finalCondition;
  std::string temp;
  SgStatement* condition = (getLoopCondition(loop));
  std::string loop1var = getLoopIndexVariable(loop)->get_name ().str();
  std::string loop2var;
  replaceExpression(condition,"col",getLoopIndexVariable(loop)->get_name ().str());
  //cout << type;
  finalCondition = isSgNode(condition)->unparseToString();       
  SgStatementPtrList& initStatements = loop->get_init_stmt();
  condition = initStatements.front();
  replaceExpression(condition,"col",getLoopIndexVariable(loop)->get_name ().str());
  const char* eqloc = strstr(condition->unparseToString().c_str(),"=");
  string test(eqloc);
  initialCondition = "col !"+test;
  initialCondition  = initialCondition.erase(initialCondition.size()-1,1);
  initialCondition = initialCondition +" - 1 ";
  finalCondition  = finalCondition.erase(finalCondition.size()-1,1);
  output ="if( "+initialCondition +" && " + finalCondition+" )\n";
  if(type ==2){
    Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(loop->get_loop_body(),V_SgForStatement);
    loop = isSgForStatement(*varList.begin());
    loop2var = getLoopIndexVariable(loop)->get_name ().str();
    //cout << loop2var;
    condition = (getLoopCondition(loop));
    replaceExpression(condition,"row",getLoopIndexVariable(loop)->get_name ().str());
    finalCondition = isSgNode(condition)->unparseToString();
    initStatements = loop->get_init_stmt();
    condition = initStatements.front();
    replaceExpression(condition,"row",getLoopIndexVariable(loop)->get_name ().str());
    const char* eqloc1 = strstr(condition->unparseToString().c_str(),"=");
    string test1(eqloc1);
    initialCondition = "row !"+test1;
    initialCondition  = initialCondition.erase(initialCondition.size()-1,1);
    initialCondition = initialCondition +" - 1 ";
    
    finalCondition  = finalCondition.erase(finalCondition.size()-1,1);
    output +="if( "+initialCondition +" && " + finalCondition+" )";
  }
  output += "{";
  Rose_STL_Container<SgNode*> loopBody = NodeQuery::querySubTree(loop->get_loop_body(),V_SgStatement);
  Rose_STL_Container<SgNode*> :: iterator it = loopBody.begin()+1;
  SgStatement* count = isSgStatement(*(loopBody.begin()+1));
  //while(count != getLastStatement(isSgScopeStatement(loop->get_loop_body())))
  do{
    string add;
    replaceExpression(count,"col",loop1var);
    add = isSgNode(count)->unparseToString();
    if(type ==2){
      replaceExpression(count,"row",loop2var);
      add = replaceString(isSgNode(count)->unparseToString(),"][","+device_N*(");
      //              cout <<add<<endl;       
      string pattern = "]";
      size_t pos = 0;
      while((pos = add.find(pattern, pos)) != std::string::npos)
      {
        add.insert(pos, ")");
        pos += 2;
        
      }
    }
    output += "\n"+add;
    it++;
    count = getNextStatement(count);
  }while(count != NULL);
  output += "}";
  cout << output <<endl;
  return output;
}


bool find( Rose_STL_Container<SgNode*> searchme, const char* value)
{
  int j = 0;
  Rose_STL_Container<SgNode*> :: iterator i=searchme.begin();
  while(i != searchme.end())
  {
    if(strcmp((*i)->unparseToString().c_str(),value)==0 || (*i)->unparseToString().find('[',0) != string::npos)
    {
      return false;
    }
    i++;
  }
  return true;
}
void insertPragmas(SgForStatement* loop,SgBasicBlock* func_body,char* part,bool offload , bool for_loop)
{
  pushScopeStack(func_body);
  string* s = new string(part);
  std::string str = "omp for reduction (";
  printf("Please enter the type of reduction you wish \n1. Addition \n2. Subtraction \n3.Min \n4.Max\n5.Multiplication");
  int choice;
  cin >> choice;
  if(choice ==1)
    str += "+ : ";
  else if (choice ==2)
    str += "- : ";
  else if (choice ==3)
    str += "min : ";
  else if (choice ==4)
    str += "max : ";
  else str +="* : ";
  
  int a =0;
  string reduce;
  Rose_STL_Container<SgNode*> sharedV;
  Rose_STL_Container<SgNode*> privateV;
  Rose_STL_Container<SgNode*> firstprivateV;
  Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(loop,V_SgVarRefExp);
  Rose_STL_Container<SgNode*> :: iterator j = varList.begin();
  Rose_STL_Container<SgNode*> :: iterator i;
  if(for_loop){
    privateV.push_back(isSgNode(getLoopIndexVariable(loop)));
    printf("\nAdding %s to private variables.\n",isSgNode(getLoopIndexVariable(loop))->unparseToString().c_str());
  }
  SgStatementPtrList& initStatements = loop->get_init_stmt();
  SgStatement* upper = getLoopCondition(loop);
  SgStatement* lower = initStatements.front();
  SgExpression* upperbound =isSgBinaryOp(isSgExprStatement(upper)->get_expression())->get_rhs_operand_i();
  SgExpression* lowerbound =isSgAssignOp(isSgExprStatement(lower)->get_expression())->get_rhs_operand_i();
  int numValues;
  char* reduceVar= (char*)malloc(256);
  
  if(for_loop){
    printf("\nPlease enter the number of variables to reduce. If there are no variables to reduce please enter 0. \n");
    cin>>numValues;
    for(int a =0;a<numValues;a++){
      char* reduceVar = (char*)malloc(256);
      SgVariableDeclaration* varDecl;
      printf("/nPlease select a variable to perform the reduce operation on.  List of possible variables are:\n");
      getVars(func_body);
      scanf("%s",reduceVar);
      varDecl = buildVariableDeclaration("temp_"+string(reduceVar),lookupNamedTypeInParentScopes(reduceVar,func_body),buildAssignInitializer(buildIntVal(0)));
      insertStatementAfter(getFirstStatement(func_body),varDecl);
      
      //getPointers(func_body);
      if(lookupVariableSymbolInParentScopes(reduceVar)==NULL)
      {
        printf("\nIllegal Variable Name!!!\n");
        exit(1);
      }
      privateV.push_back(isSgNode(lookupSymbolInParentScopes(reduceVar,func_body)->get_symbol_basis ()));
      sharedV.push_back(lookupSymbolInParentScopes("temp_"+string(reduceVar),func_body)->get_symbol_basis ());
      SgExprStatement* reduction = buildAssignStatement(buildVarRefExp("temp_"+string(reduceVar)),buildVarRefExp(reduceVar));
      insertStatementAfter(loop->get_loop_body(),reduction);
      reduction = buildAssignStatement(buildVarRefExp(reduceVar),buildVarRefExp("temp_"+string(reduceVar)));
      insertStatementAfter(loop,reduction);
      string temp  =  lookupSymbolInParentScopes(reduceVar,func_body)->get_symbol_basis ()->unparseToString();
      if (a!=numValues-1){
        str.append("temp_"+temp);
        str.append(",");}
      else str.append("temp_"+temp);
    }
  }
  str.append(" )");
  std::string *pstr = new string(str);
  SgPragmaDeclaration* test;
  if(for_loop){
    if(numValues !=0)
      test = buildPragmaDeclaration(*pstr);
    else {
      pstr = new string("omp for");
      test = buildPragmaDeclaration(*pstr);
    }
    if(isSgVarRefExp(upperbound)!=NULL)
    {
      printf("\nAdding %s to shared variables.\n",isSgNode(upperbound)->unparseToString().c_str());
      sharedV.push_back(isSgNode(upperbound));
    }
    if(isSgVarRefExp(lowerbound)!=NULL)
    {
      printf("\nAdding %s to shared variables.\n",isSgNode(lowerbound)->unparseToString().c_str());
      sharedV.push_back(isSgNode(lowerbound));
    }
    j  = varList.begin();
    while(j!=varList.end())
    {
      if( find(firstprivateV, (*j)->unparseToString().c_str()) &&( isSgPointerType(isSgVarRefExp(*j)->get_type())!=NULL|| isSgArrayType(isSgVarRefExp(*j)->get_type())!=NULL)&& strcmp(part,(*j)->unparseToString().c_str())!=0)
      {
        cout <<"\nfirstprivate variables added "<<isSgNode((*j))->unparseToString().c_str()<<" with type "<< isSgNode(isSgVarRefExp(*j)->get_type())->unparseToString().c_str()<<endl;
        firstprivateV.push_back(*j);
      }
      j++;
    }
    Rose_STL_Container<SgNode*> assignList = NodeQuery::querySubTree(loop,V_SgAssignOp);
    i = assignList.begin();
    while(i != assignList.end())
    {
      SgExpression* varexp =isSgBinaryOp(*i)->get_lhs_operand_i();
      if( find(privateV, isSgNode(varexp)->unparseToString().c_str()) && find(sharedV,isSgNode(varexp)->unparseToString().c_str()) &&  find(firstprivateV,isSgNode(varexp)->unparseToString().c_str()) )
      {
        if(strcmp(part,isSgNode(varexp)->unparseToString().c_str())!=0 && isSgNode(varexp)->unparseToString().find('[',0)==string::npos)
        {
          cout <<"\nAdding following var to private vars: "<< isSgNode(varexp)->unparseToString().c_str()<<endl;
          privateV.push_back(isSgNode(varexp));
        }
      }
      i++;
    }
    i = assignList.begin();
    while(i!=assignList.end())
    {
      SgExpression* varexp = isSgBinaryOp(*i)->get_rhs_operand_i();
      Rose_STL_Container<SgNode*> rhsList = NodeQuery::querySubTree(varexp,V_SgVarRefExp);
      j = rhsList.begin();
      while(j!=rhsList.end())
      {
        if(find(privateV, (*j)->unparseToString().c_str())  && find(firstprivateV, (*j)->unparseToString().c_str()) && find(sharedV,(*j)->unparseToString().c_str()))
        {
          printf("\nAdding %s to shared var\n",((*j)->unparseToString().c_str()));
          sharedV.push_back(isSgNode(*j));
        }
        j++;
      }
      i++;
    }
    j = varList.begin();
    while((j)!=varList.end())
    {
      if( find(privateV, (*j)->unparseToString().c_str()) &&find(sharedV,(*j)->unparseToString().c_str()) &&  find(firstprivateV, (*j)->unparseToString().c_str()))
      {
        sharedV.push_back(isSgNode(*j));
        printf("\nAdding %s to shared var\n",((*j)->unparseToString().c_str()));
      }
      j++;
    }
  }
  if(offload){
    Rose_STL_Container<SgNode*> Input;
    Rose_STL_Container<SgNode*> Output;
    Rose_STL_Container<SgNode*> InOut;
    Rose_STL_Container<SgNode*> functions =  NodeQuery::querySubTree(loop,V_SgFunctionCallExp);     
    j = functions.begin();
    while(j!=functions.end())
    {
      SgFunctionDeclaration* decl =(isSgFunctionCallExp(*j))->getAssociatedFunctionSymbol()->get_declaration ();
      if(decl != NULL){
        cout <<isSgNode(decl)->unparseToString()<<endl;
        attachArbitraryText(decl,"__declspec(target(mic))");    
      }
      j++;
    }
    j = sharedV.begin();
    int answer;
    
    while(j!=sharedV.end()){
      
      if((*j)->unparseToString().find("temp_")!=string::npos)
      {
        InOut.push_back(isSgNode(*j));
      }
      else{
        cout << "\nDo you want "<< (*j)->unparseToString().c_str()<<" to be added to \n1. Input \n2. Output \n3. Input/Output \n4. None?"<<endl;
        cin >>answer;
        switch(answer){
        case 1: Input.push_back(isSgNode(*j));break;
        case 2: Output.push_back(isSgNode(*j));break;
        case 3: InOut.push_back(isSgNode(*j));break;
        default:break;
        }
      }
      j++;
      
    }
    j = firstprivateV.begin();
    while(j!=firstprivateV.end())
    {
      cout << "Do you want "<< (*j)->unparseToString().c_str()<<" to be added to "<<endl<<"1. Input"<<endl<<"2. Output"<<endl<<"3. Input/Output"<<endl<<"4. None?"<<endl;
      cin >>answer;
      
      
      
      
      switch(answer){
      case 1: Input.push_back(isSgNode(*j));break;
      case 2: Output.push_back(isSgNode(*j));break;
      case 3: InOut.push_back(isSgNode(*j));break;
      default:break;
      
      
      }
      j++;
    }
    string str1 = "offload target (mic) ";
    j = Input.begin();
    Rose_STL_Container<SgNode*> arrays;
    Rose_STL_Container<SgNode*> variables;
    while(j != Input.end())
    {
      if(lookupNamedTypeInParentScopes((*j)->unparseToString())->containsInternalTypes())
      {
        arrays.push_back(*j);
      }
      else{ 
        variables.push_back(*j);
      }
      
      j++;
    }
    j = variables.begin();
    if(j!= variables.end())
      str1.append(" in(");
    
    while(j!= variables.end())
    {
      str1.append((*j)->unparseToString().c_str());
      if((j+1)!=variables.end())
        str1.append(",");
      else str1.append(") ");
      j++;
    }
    
    j = arrays.begin();
    while(j!=arrays.end()){
      printf("What is the length of the array ");
      cout <<(*j)->unparseToString()<<endl;
      string length;
      cin >> length;
      str1.append("in( "+(*j)->unparseToString()+":length("+length+")) ");
      j++;
    }
    
    j = Output.begin();
    arrays.clear();
    variables.clear();
    while(j != Output.end())
    {
      if(lookupNamedTypeInParentScopes((*j)->unparseToString())->containsInternalTypes())
      {       
        arrays.push_back(*j);
      }
      else{
        variables.push_back(*j);
      }
      
      j++;
    }
    j = variables.begin();
    if(j!= variables.end())
      str1.append(" out(");
    
    while(j!= variables.end())
    {
      str1.append((*j)->unparseToString().c_str());
      if((j+1)!=variables.end())
        str1.append(",");
      else str1.append(") ");
      j++;
    }
    
    j = arrays.begin();
    while(j!=arrays.end()){
      printf("What is the length of the array ");
      cout <<(*j)->unparseToString()<<endl;
      string length;
      cin >> length;
      str1.append("out( "+(*j)->unparseToString()+":length("+length+")) ");
      j++;
    }
    
    j = InOut.begin();
    arrays.clear();
    variables.clear();
    while(j != InOut.end())
    {
      if(lookupNamedTypeInParentScopes((*j)->unparseToString())->containsInternalTypes())
      {
        arrays.push_back(*j);
      }
      else{
        variables.push_back(*j);
      }
      
      j++;
    }
    j = variables.begin();
    if(j!= variables.end())
      str1.append(" inout(");
    
    while(j!= variables.end())
    {
      str1.append((*j)->unparseToString().c_str());
      if((j+1)!=variables.end())
        str1.append(",");
      else str1.append(") ");
      j++;
    }
    
    j = arrays.begin();
    while(j!=arrays.end()){
      printf("What is the length of the array ");
      cout <<(*j)->unparseToString()<<endl;
      string length;
      cin >> length;
      str1.append("inout( "+(*j)->unparseToString()+":length("+length+")) ");
      j++;
    }
    
    
    
    string* vprag = new string(str1);
    SgPragmaDeclaration* varPragma = buildPragmaDeclaration(*vprag);
    insertStatementBefore(loop,varPragma);
    //attachArbitraryText(loop,str1);
  }
  
  j = varList.begin();
  if(for_loop){
    str = "omp parallel default(none) shared(";
    Rose_STL_Container<SgNode*> :: iterator l = sharedV.begin();
    while((l) != sharedV.end())
    {
      str.append((*l)->unparseToString().c_str());
      if((l+1)!=sharedV.end())
        str.append(",");
      l++;
    }
    
    str.append(") private(");
    l = privateV.begin();
    while((l) != privateV.end())
    {
      str.append((*l)->unparseToString().c_str());
      if((l+1)!=privateV.end())
        str.append(",");
      l++;
    }
    if(firstprivateV.begin()!=firstprivateV.end()){
      str.append(") firstprivate(");
      l = firstprivateV.begin();
      while((l) != firstprivateV.end())
      {
        str.append((*l)->unparseToString().c_str());
        if((l+1)!=firstprivateV.end())
          str.append(",");
        l++;
      }}
    str.append(")");
    string* vprag = new string(str);
    SgPragmaDeclaration* varPragma = buildPragmaDeclaration(*vprag);
    
    insertStatementBefore(loop,varPragma);
    attachArbitraryText(varPragma,"{",PreprocessingInfo::after);
  }
  printf("Are there any lines of code that you would like to run by a single thread at a time?(Y/N)");
  char in;
  cin >> in;
  if(in =='y' || in =='Y')
  {
    bool condition = true;
    char cond;
    while(condition){
      //insert code for omp critical
      writeToFile(*(isSgBasicBlock(loop->get_loop_body())->get_statements ().begin()));
      printf("\nFor your convenience all the statements in this loop have been copied into a file called numberedCode.C.  Please insert the line number where you would like to insert the critical pragma.  If there is more than one line, please use a dash to specify the lines.\n");
      std::string lines;
      cin>>lines;
      std::string start;
      std::string end;
      if(lines.find('-',0)!= string::npos){
        //if dash is contained mult lines code
        start = lines.substr(0,lines.find('-',0)-1);
        end = lines.substr(lines.find('-',0)+1,lines.size()-1);
      }
      else{
        start = lines;
        end = "";
      }
      
      //convert to int and get statement
      int lineNumber = atoi(lines.c_str());
      SgStatement* exc = (*(isSgBasicBlock(loop->get_loop_body())->get_statements ().begin()));
      int i ;
      for ( i = 1; i<lineNumber;i++){
        exc = getNextStatement(exc);
      }
      SgPragmaDeclaration* prag = buildPragmaDeclaration("omp critical");
      insertStatementBefore(exc,prag);
      
      if(end.compare("")!=0)
      {
        attachArbitraryText(exc,"{",PreprocessingInfo::before);
        for(i=atoi(start.c_str());i<atoi(end.c_str())-1;i++)
        {
          exc = getNextStatement(exc);
        }
        attachArbitraryText(exc,"}",PreprocessingInfo::after);
      }
      printf("Are there any other places in the loop you would like to run by a single thread at a time?(Y/N)");
      cin >>cond;
      if(cond =='n' || cond =='N')
        condition =false;
    }
  }
  insertStatementBefore(loop,test);
  if(for_loop)
    attachArbitraryText(loop,"}",PreprocessingInfo::after);
  
  popScopeStack();
}
SgBasicBlock* getFunction(){
  cin>>name;
  if(lookupFunctionSymbolInParentScopes(SgName(name))!=NULL){
    
    Rose_STL_Container<SgNode*> functionDeclarationList = NodeQuery::querySubTree(getProject(),V_SgFunctionDeclaration);
    for(Rose_STL_Container<SgNode*>::iterator i = functionDeclarationList.begin();i<functionDeclarationList.end();i++)
    {
      SgFunctionDeclaration* functionDeclaration = isSgFunctionDeclaration(*i);
      ROSE_ASSERT(functionDeclaration!=NULL);
      if((*i)->get_file_info()->isCompilerGenerated()==false)
      {
        if(name.compare(functionDeclaration->get_name().str())==0)
        {
          if(functionDeclaration->get_definition()!=NULL)
          {
            return functionDeclaration->get_definition()->get_body ();
          }
        }
      }
    }
  }
  else{
    printf("\nSorry, that method name does not exist in your function.\n");
    exit(1);
  }
}
void getPointers(SgBasicBlock* loop){
  Rose_STL_Container<SgNode*> assignList = NodeQuery::querySubTree(loop,V_SgAssignOp);
  Rose_STL_Container<SgNode*> pointerList = NodeQuery::querySubTree(loop,V_SgVarRefExp);
  Rose_STL_Container<SgNode*> endList;
  Rose_STL_Container<SgNode*> :: iterator i = assignList.begin()+1;
  Rose_STL_Container<SgNode*> :: iterator j = pointerList.begin();
  Rose_STL_Container<SgNode*>  list = NodeQuery::querySubTree(loop,V_SgForStatement);
  while(i!=assignList.end())
  {
    SgExpression* varexp =isSgBinaryOp(*i)->get_lhs_operand_i();
    if(find(endList,isSgNode(varexp)->unparseToString().c_str())&&(lookupNamedTypeInParentScopes(isSgNode(varexp)->unparseToString().c_str(),loop)->containsInternalTypes()))
      endList.push_back(isSgNode(varexp));
    i++;
  }
  while(j!=pointerList.end())
  {
    if(isSgPointerType(isSgVarRefExp(*j)->get_type())!=NULL){
      const char* temp = isSgNode(*j)->unparseToString().c_str();
      if(find(endList,temp)&& (lookupNamedTypeInParentScopes(temp,loop)->containsInternalTypes())){
        endList.push_back(*j);
      }
    }
    j++;
  }
  i = endList.begin();
  while(i!=endList.end())
  {
    bool canPrint = true;
    j = list.begin();
    while(j!=list.end())
    {
      SgInitializedName* loopVar = getLoopIndexVariable(*j);
      if(strcmp(loopVar->get_name().str(),isSgNode(*i)->unparseToString().c_str()) == 0)
      {
        canPrint = false;
      }
      j++;
    }
    if(canPrint && lookupNamedTypeInParentScopes(isSgNode(*i)->unparseToString().c_str(),loop)!=NULL)
      printf("%s  type is %s\n",isSgNode(*i)->unparseToString().c_str(),isSgNode(lookupNamedTypeInParentScopes(isSgNode(*i)->unparseToString().c_str(),loop))->unparseToString().c_str());
    i++;
  }
  
  
}

void getVars(SgBasicBlock* loop)
{
  pushScopeStack(loop);
  Rose_STL_Container<SgNode*> assignList = NodeQuery::querySubTree(loop,V_SgAssignOp);
  Rose_STL_Container<SgNode*> pointerList = NodeQuery::querySubTree(loop,V_SgVarRefExp);
  Rose_STL_Container<SgNode*> endList;
  Rose_STL_Container<SgNode*> :: iterator i = assignList.begin()+1;
  Rose_STL_Container<SgNode*> :: iterator j = pointerList.begin()+1;
  Rose_STL_Container<SgNode*>  list = NodeQuery::querySubTree(loop,V_SgForStatement);
  
  /*        while(i!=assignList.end())
  {
  SgExpression* varexp =isSgBinaryOp(*i)->get_lhs_operand_i();
  //              cout <<isSgNode(varexp)->unparseToString().c_str()<<" , ";
  if(find(endList,isSgNode(varexp)->unparseToString().c_str())&&!(lookupNamedTypeInParentScopes(isSgNode(varexp)->unparseToString().c_str(),loop)->containsInternalTypes()))
  if(isSgNode(varexp)->unparseToString().find("[")==-1)
  {
  endList.push_back(isSgNode(varexp));
  //cout <<isSgNode(varexp)->unparseToString().c_str()<<" , ";
  }
  i++;
  
  }*/
  
  while(j!=pointerList.end())
  {
    //       cout <<isSgNode(*j)->unparseToString().c_str()<<" , ";  
    if((isSgVarRefExp(*j)->get_type())!=NULL){
      //cout <<isSgNode(*j)->unparseToString().c_str()<<" , ";
      const char* temp = isSgNode(*j)->unparseToString().c_str();
      
      if(find(endList, isSgNode(*j)->unparseToString().c_str())&& !(lookupNamedTypeInParentScopes(temp,loop)->containsInternalTypes())){
        endList.push_back(*j);
        //cout <<isSgNode(*j)->unparseToString().c_str()<<" , ";
      }
    }
    j++;
  }
  i = endList.begin();
  while(i!=endList.end())
  {
    bool canPrint = true;
    j = list.begin();
    while(j!=list.end())
    {
      SgInitializedName* loopVar = getLoopIndexVariable(*j);
      if(strcmp(loopVar->get_name().str(),isSgNode(*i)->unparseToString().c_str()) == 0)
      {
        canPrint = false;
      }
      j++;
    }
    if(canPrint && lookupNamedTypeInParentScopes(isSgNode(*i)->unparseToString().c_str())!=NULL)
      cout << isSgNode(*i)->unparseToString() << " type is " <<isSgNode(lookupNamedTypeInParentScopes(isSgNode(*i)->unparseToString().c_str(),loop))->unparseToString() <<endl;
    //                         printf("%s  type is %s\n",isSgNode(*i)->unparseToString().c_str(),isSgNode(lookupNamedTypeInParentScopes(isSgNode(*i)->unparseToString().c_str(),loop))->unparseToString().c_str());
    i++;
  }
  popScopeStack();
}

SgNode* getForStatement(SgBasicBlock* func_body,SgProject* project){
  bool rightStatement=false;
  Rose_STL_Container<SgNode*> init = NodeQuery::querySubTree(func_body,V_SgForStatement);
  Rose_STL_Container<SgNode*> :: iterator i = init.begin();
  if(init.size()==0){
    printf("\nSorry no For Loops in target method.\n");
    exit(1);
  }
  while(i!=init.end())
  {
    printf("\n%s\nIs this the for loop you are looking for?(y/n) \n",(*i)->unparseToString().c_str());
    char check= getchar();
    check = getchar();
    if(check == 'y'||check == 'Y')
      return *i;
    i++;
  }
  char checkCond;
  printf("\nIs there a region of code that needs to be parallelized? \n");
  cin >> checkCond;
  //        printf("Sorry there are no other for loops so program will now exit.\n");
  exit(1);
  return *i;
}
void insertHeaders(SgGlobal* globalscope)
{
  if(which_language == 1)
    insertHeader("mpi.h",PreprocessingInfo::after,true,globalscope);
  
  else if(which_language == 2)
  {
    insertHeader("omp.h",PreprocessingInfo::before,true,globalscope);
  }
}
void insertHeaders_stencil(SgGlobal* globalscope)
{
  insertHeader("LinearMapping.h",PreprocessingInfo::after,false,globalscope);
  insertHeader("split.h",PreprocessingInfo::after,false,globalscope);
  insertHeader("comm.h",PreprocessingInfo::after,false,globalscope);
  insertHeader("exchange.h",PreprocessingInfo::after,false,globalscope);
  insertHeader("collect.h",PreprocessingInfo::after,false,globalscope);
}
/*generalMPI
*contains the size and rank along with their function calls
*
*/
void generalMPI(SgBasicBlock* body)
{
  if(lookupSymbolInParentScopes("rose_rank",body)==NULL){
    pushScopeStack(body);
    SgVariableDeclaration* variableDeclaration = buildVariableDeclaration("rose_rank",buildIntType());
    prependStatement(variableDeclaration,body);
    variableDeclaration = buildVariableDeclaration("rose_size",buildIntType());
    prependStatement(variableDeclaration,body);
    if (body != NULL)
    {
      SgExprListExp* args2 = buildExprListExp(buildOpaqueVarRefExp("MPI_COMM_WORLD", body), buildAddressOfOp(buildVarRefExp(SgName("rose_rank"), body)));
      SgExprListExp* args3 = buildExprListExp(buildOpaqueVarRefExp("MPI_COMM_WORLD", body), buildAddressOfOp(buildVarRefExp(SgName("rose_size"), body)));
      SgType* return_type = buildIntType();
      const unsigned int SIZE_OF_BLOCK = 1;
      if (body->get_statements().size() > SIZE_OF_BLOCK)
      {
        SgExprStatement* callStmt3 = buildFunctionCallStmt(SgName("MPI_Comm_rank"),return_type,args2,body);
        SgExprStatement* callStmt4 = buildFunctionCallStmt(SgName("MPI_Comm_size"),return_type,args3,body);
        SgStatement* lastDeclarationStatement = getFirstStatement(body);
        while(isSgVariableDeclaration(lastDeclarationStatement)!=NULL)
          lastDeclarationStatement = getNextStatement(lastDeclarationStatement);
        if (lastDeclarationStatement != NULL)
        {
          insertStatementAfter (lastDeclarationStatement, callStmt3);
          insertStatementAfter (lastDeclarationStatement, callStmt4);
        }
      }
    }
    popScopeStack();}
}
char* variableDeclarations_OpenMP(SgBasicBlock* body, SgForStatement* loop)
{
  char* reduceVar = (char*)malloc(256);
  printf("\nPlease select a variable to perform the reduce operation on.  List of possible variables are:\n ");
  getVars(body);
  scanf("%s",reduceVar);
  pushScopeStack(body);
  if(lookupVariableSymbolInParentScopes(reduceVar)==NULL)
  {
    printf("Illegal Variable Name!!!\n");
    exit(1);
  }
  popScopeStack();
  return reduceVar;
}
/*
* upper limit lower limit and reduce statement
*/
void arrayFor(SgBasicBlock* body,SgForStatement* loop,int count,char* reduceVar){
  int i;
  printf("Is this a \n1. 1d array 2. \n2d array?");
  cin >> i;
  if(i==1)
  {
    SgVariableDeclaration* decl; 
    SgStatement* insertion;
    if(lookupVariableSymbolInParentScopes("rose_temp",body)==NULL){
      decl = buildVariableDeclaration("rose_temp",buildIntType());
      insertStatementAfter(loop,decl);
      insertion = decl;
      decl = buildVariableDeclaration("rose_i",buildIntType());
      insertStatementAfter(loop,decl);         
      decl = buildVariableDeclaration("rose_k",buildIntType());
      insertStatementAfter(loop,decl);
      
    }else insertion = isSgStatement(lookupVariableSymbolInParentScopes("rose_temp",body)->get_declaration()->get_declaration());
    decl = buildVariableDeclaration("rose_"+string(reduceVar),lookupNamedTypeInParentScopes(reduceVar));
    insertStatementAfter(loop,decl);
    //                decl = buildVariableDeclaration("rose_i",buildIntType());
    //                insertStatementAfter(loop,decl);
    //              SgStatement* insertion = getNextStatement(decl2);
    attachArbitraryText(insertion, " rose_k = rose_lower_limit0;for(rose_i=0; rose_i< (rose_upper_limit0 - rose_lower_limit0); rose_i++){rose_"+string(reduceVar)+"[rose_i]="+reduceVar+"[rose_k];rose_k++;}");             
    string test;
    if(isSgTypeDouble(lookupNamedTypeInParentScopes(reduceVar,body)->findBaseType())!=NULL)
      test = "MPI_DOUBLE";
    else test = "MPI_INT";
    attachArbitraryText(insertion, "MPI_Allgather(rose_"+string(reduceVar)+",rose_upper_limit0-rose_lower_limit0,"+test+","+string(reduceVar)+",(rose_upper_limit0-rose_lower_limit0),"+test+",MPI_COMM_WORLD);");
    
    
  }
  else{
    SgVariableDeclaration* decl;
    SgStatement* insertion;
    if(lookupVariableSymbolInParentScopes("rose_temp",body)==NULL){
      decl = buildVariableDeclaration("rose_temp",buildIntType());
      insertStatementAfter(loop,decl);
      insertion = decl;
      decl = buildVariableDeclaration("rose_i",buildIntType());
      insertStatementAfter(loop,decl);
      decl = buildVariableDeclaration("rose_j",buildIntType());
      insertStatementAfter(loop,decl);
      decl = buildVariableDeclaration("rose_k",buildIntType());
      insertStatementAfter(loop,decl);
    }else insertion = isSgStatement(lookupVariableSymbolInParentScopes("rose_temp",body)->get_declaration()->get_declaration());
    decl = buildVariableDeclaration("rose_"+string(reduceVar),lookupNamedTypeInParentScopes(reduceVar));
    insertStatementAfter(loop,decl);
    string row;
    printf("Please enter the number of rows in the array. ");
    cin >> row;
    attachArbitraryText(insertion, " rose_k = rose_lower_limit0;for(rose_i=0; rose_i< (rose_upper_limit0 - rose_lower_limit0); rose_i++){ for(rose_j=0;rose_j<"+row+";rose_j++){rose_"+string(reduceVar)+"[rose_i][rose_j]="+reduceVar+"[rose_k][rose_j];rose_k++;}}");
    string test;
    if(isSgTypeDouble(lookupNamedTypeInParentScopes(reduceVar,body)->findBaseType())!=NULL)
      test = "MPI_DOUBLE";
    else test = "MPI_INT";
    attachArbitraryText(insertion, "MPI_Allgather(rose_"+string(reduceVar)+",rose_upper_limit0-rose_lower_limit0,"+test+","+string(reduceVar)+",(rose_upper_limit0-rose_lower_limit0),"+test+",MPI_COMM_WORLD);");
  }
}
void variableDeclarations_MPI(SgBasicBlock* body,SgForStatement* loop,int count)
{
  pushScopeStack(body);
  int numVars,i;
  printf("\nPlease enter the number of variables that you would like to perform reduction operations on. If there are no variables to reduce please enter 0.\n");
  cin>>numVars;
  char* reduceVar = (char*)malloc(256);
  char* upperLim= (char*)malloc(21);
  sprintf(upperLim,"rose_upper_limit%d",count);
  char* lowerLim = (char*)malloc(21);
  sprintf(lowerLim,"rose_lower_limit%d",count);
  SgVariableDeclaration *variableDeclaration;/* = buildVariableDeclaration(upperLim,buildIntType());
  prependStatement(variableDeclaration,body);
  variableDeclaration = buildVariableDeclaration(lowerLim,buildIntType());
  prependStatement(variableDeclaration,body);
  */         for(i=0;i<numVars;i++)
  {
    printf("/nPlease select a variable to perform the reduce operation on.  List of possible variables are:\n");
    if(loop != NULL)
      getVars(isSgBasicBlock(getLoopBody(loop)));
    else getVars(body);
    cin>>reduceVar;
    // pushScopeStack(body);
    if(lookupVariableSymbolInParentScopes(reduceVar)==NULL)
    {
      printf("Illegal Variable Name!!!\n");
      exit(1);
    }
    if(isSgPointerType(lookupNamedTypeInParentScopes(reduceVar,body))!=NULL||isSgArrayType(lookupNamedTypeInParentScopes(reduceVar,body))!=NULL){
      printf("\nPlease note the variable you are reducing is an array.  This will use an allgather for data collection instead of an allreduce.\n");
      arrayFor(body,loop,count, reduceVar);
    }
    else{
      string temp = "rose_";
      char* tempo = new char[temp.size()+1];
      std::copy(temp.begin(),temp.end(),tempo);
      char* varl = (char*) malloc(strlen(strcat(tempo,reduceVar))+5);
      sprintf(varl,"%s%d",tempo,count);
      if(lookupVariableSymbolInParentScopes(varl,body)==NULL){
        variableDeclaration = buildVariableDeclaration(varl,lookupVariableSymbolInParentScopes(reduceVar)->get_type());
        prependStatement(variableDeclaration,body);
      }
      SgExprStatement* afterstmt = buildAssignStatement(buildVarRefExp(reduceVar),buildVarRefExp(varl));
      insertStatementAfter(loop,afterstmt);
      SgExprListExp* args5;
      int choice;
      printf("\nPlease select the reduce operation to use for variable \n1. Sum \n2. Product \n3. Min \n4. Max. \n");
      cin >>choice;
      string operation;
      switch(choice){
      case 1:operation = "MPI_SUM";break;
      case 2:operation = "MPI_PRODUCT";break;
      case 3: operation = "MPI_MIN";break;
      default:operation = "MPI_MAX";break;
      }
      if(isSgTypeDouble(lookupVariableSymbolInParentScopes(reduceVar)->get_type())!=NULL)
        args5 = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_DOUBLE", body),buildOpaqueVarRefExp(operation, body),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
      else{
        args5 = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_INT", body),buildOpaqueVarRefExp(operation, body),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
        //printf("\n\n\n\n\n\n");
      }
      int x;
      printf("\nWould you like to send the results after reducing the chosen variable to all processes or to only one?(1. all 0. one) ");
      cin>>x;
      if(x==0){
        SgExprStatement* callStmt5 = buildFunctionCallStmt(SgName("MPI_Reduce"),buildIntType(),args5,body);
        insertStatementAfter (loop,callStmt5);
      }
      else{
        
        SgExprStatement* callStmt5 = buildFunctionCallStmt(SgName("MPI_Allreduce"),buildIntType(),args5,body);
        insertStatementAfter (loop,callStmt5);
      }
    }
  }
  printf("\nVariable Declarations complete.\n");
  popScopeStack();
  
}
void setForLoopBounds_MPI(SgForStatement* loop,int count){
  pushScopeStack(loop->get_parent());
  char* upperLim = (char*)malloc(21);
  sprintf(upperLim,"rose_upper_limit%d",count);
  char* lowerLim = (char*)malloc(21);
  sprintf(lowerLim,"rose_lower_limit%d",count);
  
  setLoopLowerBound(loop,buildVarRefExp(lowerLim));
  setLoopUpperBound(loop,buildVarRefExp(upperLim));
  popScopeStack();
}
void stencil_generalOps(SgBasicBlock* body,string passedRows,string passedCols,SgStatement* exc)
{
  static vector <string> rowList;
  static vector <string> colList;
  
  //if rows and cols are found then set found to true;
  if(std::find(rowList.begin(),rowList.end(),passedRows)==rowList.end()&&std::find(colList.begin(),colList.end(),passedCols)==colList.end())
  {
    numTimes++;
    pushScopeStack(body);
    //      printf("Creating vars\n\n\n\n");
    rowList.push_back(passedRows);
    colList.push_back(passedCols);
    //stringstream in;
    char in[21];
    sprintf(in,"%d",numTimes);
    string test(in);
    SgVariableDeclaration* variableDeclaration = buildVariableDeclaration("p"+test,buildIntType());
    prependStatement(variableDeclaration,body);
    variableDeclaration = buildVariableDeclaration("q"+test,buildIntType());
    prependStatement(variableDeclaration,body);
    variableDeclaration = buildVariableDeclaration("myrows"+test,buildIntType());
    prependStatement(variableDeclaration,body);
    variableDeclaration = buildVariableDeclaration("mycols"+test,buildIntType());
    prependStatement(variableDeclaration,body);
    variableDeclaration = buildVariableDeclaration("P"+test,buildIntType());
    prependStatement(variableDeclaration,body);
    attachArbitraryText(variableDeclaration,"int Q"+test+";",PreprocessingInfo::before);
    /*              variableDeclaration = buildVariableDeclaration("Q"+test,buildIntType());
    insertStatementBefore(findLastDeclarationStatement(body),variableDeclaration);
    */              string rows = passedRows;
    string cols = passedCols;
    
    attachArbitraryText(variableDeclaration,"MPI_Comm comm2d,rowcomm,colcomm,diag1comm, diag2comm;",PreprocessingInfo::before);
    attachArbitraryText(variableDeclaration,"LinearMapping<int> rowmap, colmap;",PreprocessingInfo::before);
    //SgExprListExp* argsin = buildExprListExp((buildOpaqueVarRefExp("MPI_COMM_WORLD",body)), buildAddressOfOp(buildOpaqueVarRefExp("comm2d",body)),buildAddressOfOp(buildOpaqueVarRefExp("rowcomm")),buildAddressOfOp(buildOpaqueVarRefExp("colcomm", body)),buildAddressOfOp(buildVarRefExp("P"+test, body)),buildAddressOfOp(buildOpaqueVarRefExp("Q"+test, body)), buildAddressOfOp(buildVarRefExp("p"+test, body)),buildAddressOfOp(buildVarRefExp("q"+test, body)));
    //SgExprStatement* callStmt6 = buildFunctionCallStmt(SgName("create_2dgrid"),buildIntType(),argsin,body);
    attachArbitraryText(findMain(getProject()),"void create_2dgrid(MPI_Comm,MPI_Comm*, MPI_Comm*,MPI_Comm*,int *, int*, int*, int*);",PreprocessingInfo::before);
    attachArbitraryText(findMain(getProject()),"void create_diagcomm(MPI_Comm, int, int, int, MPI_Comm*, MPI_Comm*);",PreprocessingInfo::before);
    SgStatement* target = getFirstStatement(body);
    while(isSgVariableDeclaration(target)!=NULL)
      target = getNextStatement(target);
    
    
    target = getNextStatement(target);
    attachArbitraryText(exc,"create_2dgrid(MPI_COMM_WORLD, &comm2d, &rowcomm, &colcomm, &P"+test+", &Q"+test+", &p"+test+", &q"+test+");",PreprocessingInfo::before);
    attachArbitraryText(exc,"create_diagcomm(MPI_COMM_WORLD, rose_size,p"+test+", q"+test+",&diag1comm, &diag2comm);",PreprocessingInfo::before);
    //insertStatementBefore(target,callStmt6);
    string part1 = "rowmap.init( ";
    string part2 =  ",P"+test+",p"+test+");";
    string final = part1 + rows+part2;
    attachArbitraryText(exc,final,PreprocessingInfo::before);
    attachArbitraryText(exc,"colmap.init("+cols+",Q"+test+",q"+test+");",PreprocessingInfo::before);
    attachArbitraryText(exc,"myrows"+test+" = rowmap.getMyCount();",PreprocessingInfo::before);
    attachArbitraryText(exc,"mycols"+test+" = colmap.getMyCount();",PreprocessingInfo::before);
    attachArbitraryText(exc,"tempM_fraspa="+rows+";",PreprocessingInfo::before);
    attachArbitraryText(exc,"tempN_fraspa="+cols+";",PreprocessingInfo::before);
    attachArbitraryText(exc,cols+"=mycols"+test+";",PreprocessingInfo::before);
    attachArbitraryText(exc,rows+"=myrows"+test+";",PreprocessingInfo::before);
    popScopeStack();
  }
}
/*contains code for all reduce and reduce*/
void insertReduceOp(int count){
  printf("\nPlease select the function in which you wish to insert data collection of a variable.\n");
  SgBasicBlock* body = getFunction();
  int numVars,i;
  printf("\nPlease enter the number of variables that you would like to reduce. If there are no variables to reduce please enter 0. \n");
  cin>>numVars;
  char* reduceVar = (char*)malloc(256);
  int pos,number;
  writeToFile(getFirstStatement(body));
  
  printf("\nFor your convenience we have generated a file called numberedCode.C with line numbers on each line of your code. Please insert the line number at which you would like the reduce statement. \n");
  cin >> number;
  printf("\nWould you like the statement\n1. before\n2. after\n3. in the statement\n");
  cin >> pos;
  SgStatement* exc = (getFirstStatement(body));
  for ( i = 0; i<number;i++){
    exc = getNextStatement(exc);
    //                        cout<<"Statement  "<<i<<" is "<<isSgNode(exc)->unparseToString().c_str()<<endl;
    
  }
  if(pos ==2)
    exc = getNextStatement(exc);
  else if (pos==3)
  {
    //write to file and ask user again this time with loop body
    Rose_STL_Container<SgNode*> varList = NodeQuery::querySubTree(exc,V_SgStatement);
    Rose_STL_Container<SgStatement*> :: iterator j ;
    Rose_STL_Container<SgStatement*> list =getScope(isSgStatement(*(varList.end()-1)))->getStatementList();
    //                        printf("%s",isSgNode(*(varList.end()-1))->unparseToString().c_str());
    j = list.begin();
    exc = userFileChoice(list,&pos);
  }
  int choice;
  for(i=0;i<numVars;i++)
  {
    printf("\nPlease select a variable to perform the reduce operation on.\n");
    cin>>reduceVar;
    printf("\nPlease select the reduce operation to use for variable \n1. Sum \n2. Product \n3. Min \n4. Max. \n");
    cin >>choice;
    pushScopeStack(body);
    if(lookupVariableSymbolInParentScopes(reduceVar)==NULL)
    {
      printf("Illegal Variable Name!!!\n");
      exit(1);
    }
    string temp = "rose_";
    char* tempo = new char[temp.size()+1];
    std::copy(temp.begin(),temp.end(),tempo);
    char* varl =(char*) malloc(strlen(strcat(tempo,reduceVar)+5));
    sprintf(varl,"%s%d",tempo,count);
    SgVariableDeclaration* variableDeclaration = buildVariableDeclaration(varl,buildIntType());
    prependStatement(variableDeclaration,body);
    SgExprStatement* afterstmt = buildAssignStatement(buildVarRefExp(reduceVar),buildVarRefExp(varl));
    afterstmt->set_parent(body);
    insertStatementAfter(exc,afterstmt);
    int x;
    printf("\nWould you like to send the results after reducing the chosen variable to all processes or to only one?(1. all 0. one) \n");
    cin>>x;
    if(x==0){
      SgExprListExp* args5 = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_DOUBLE", body),buildOpaqueVarRefExp("MPI_SUM", body),buildIntVal(0),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
      SgExprStatement* callStmt5;
      if(choice ==1)
        callStmt5 = buildFunctionCallStmt(SgName("MPI_Reduce"),buildIntType(),args5,body);
      else if (choice==2)
        callStmt5 = buildFunctionCallStmt(SgName("MPI_Product"),buildIntType(),args5,body);
      else if (choice==3)
        callStmt5 = buildFunctionCallStmt(SgName("MPI_Min"),buildIntType(),args5,body);
      else if (choice==4)
        callStmt5 = buildFunctionCallStmt(SgName("MPI_Max"),buildIntType(),args5,body);
      insertStatementAfter (exc,callStmt5);
    }
    
    else{
      SgExprListExp* argsin = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_DOUBLE", body),buildOpaqueVarRefExp("MPI_SUM", body),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
      SgExprStatement* callStmt6 = buildFunctionCallStmt(SgName("MPI_Allreduce"),buildIntType(),argsin,body);
      insertStatementAfter(exc,callStmt6);
      SgExprStatement* allReduce = buildAssignStatement(buildVarRefExp(reduceVar),buildVarRefExp(varl));
      insertStatementAfter(exc,allReduce);
    }
  }
  popScopeStack();
}
SgStatement* variableDeclarations_stencil(SgBasicBlock* body,SgForStatement* loop,int count)
{
  int numVars,i,pos;
  printf("\nHow many reductions do you want? \n");
  //        printf("\nPlease enter the number of variables that you would like to reduce. If there are no variables to reduce please enter 0. \n");
  cin>>numVars;
  char* reduceVar = (char*)malloc(256);
  int choice;
  SgExprStatement* callStmt6 ;
  SgStatement* choices;
  bool location;
  for(i=0;i<numVars;i++)
  {
    printf("\nPlease select the function in which you wish to insert data collection of a variable.\n");
    body = getFunction();
    
    printf("\nPlease select a variable to perform the reduce operation on.  \n ");
    if(body!=NULL){
      getVars(body);
      
      cin>>reduceVar;
      printf("\nPlease select the reduce operation to use for variable \n1. sum \n2. Product \n3. Min \n4. Max. \n");
      cin >>choice;
      pushScopeStack(body);
      if(lookupVariableSymbolInParentScopes(reduceVar)==NULL)
      {
        printf("Illegal Variable Name!!!\n");
        exit(1);
      }
      string temp = "rose_";
      char* tempo = new char[temp.size()+1];
      std::copy(temp.begin(),temp.end(),tempo);
      char* varl =(char*) malloc(strlen(strcat(tempo,reduceVar)+5));
      sprintf(varl,"%s%d",tempo,count);
      if(lookupVariableSymbolInParentScopes(varl,body)==NULL){
        SgVariableDeclaration* variableDeclaration = buildVariableDeclaration(varl,lookupNamedTypeInParentScopes(reduceVar,body));
        prependStatement(variableDeclaration,body);
      }
      SgExprStatement* afterstmt = buildAssignStatement(buildVarRefExp(reduceVar),buildVarRefExp(varl));
      afterstmt->set_parent(body);
      printf("\nPlease enter where you would like to collect the data. \n");
      choices = userFileChoice(body->get_statements(),&pos);
      //   insertStatementAfter(choices,afterstmt);
      if(pos ==1)location = true;
      else location = false;
      int x;
      printf("\nWould you like to send the results after reducing the chosen variable to all processes or to only one?(1. all 0. one) \n");
      cin>>x;
      if(x==0){
        SgExprListExp* args5;
        //                      printf("%sn\n\n\n", isSgNode(lookupNamedTypeInParentScopes(reduceVar,body))->unparseToString().c_str());
        if(isSgTypeInt(lookupNamedTypeInParentScopes(reduceVar)) != NULL){
          args5 = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_INT", body),buildOpaqueVarRefExp("MPI_SUM", body),buildIntVal(0),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
        }                       else
          args5 = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_DOUBLE", body),buildOpaqueVarRefExp("MPI_SUM", body),buildIntVal(0),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
        
        SgExprStatement* callStmt5;
        if(choice ==1)
          callStmt5 = buildFunctionCallStmt(SgName("MPI_Reduce"),buildIntType(),args5,body);
        else if (choice==2)
          callStmt5 = buildFunctionCallStmt(SgName("MPI_Product"),buildIntType(),args5,body);
        else if (choice==3)
          callStmt5 = buildFunctionCallStmt(SgName("MPI_Min"),buildIntType(),args5,body);
        else if (choice==4)
          callStmt5 = buildFunctionCallStmt(SgName("MPI_Max"),buildIntType(),args5,body);
        
        
        
        if(location)
        {
          
          insertStatement(choices,callStmt5,location, true);
          insertStatement(choices,afterstmt,location,true);
        }
        else{
          insertStatement(choices,afterstmt,location,true);
          insertStatement(choices,callStmt5,location, true);
        }
      }
      else{
        SgExprListExp* argsin;
        if(isSgTypeInt(lookupNamedTypeInParentScopes(reduceVar)) != NULL){
          argsin = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_INT", body),buildOpaqueVarRefExp("MPI_SUM", body),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
          
        }
        else argsin = buildExprListExp(buildAddressOfOp(buildVarRefExp(reduceVar,body)), buildAddressOfOp(buildVarRefExp(varl,body)),buildIntVal(1),buildOpaqueVarRefExp("MPI_DOUBLE", body),buildOpaqueVarRefExp("MPI_SUM", body),buildOpaqueVarRefExp("MPI_COMM_WORLD", body));
        callStmt6 = buildFunctionCallStmt(SgName("MPI_Allreduce"),buildIntType(),argsin,body);
        if(location)
        {
          
          insertStatement(choices,callStmt6,location, true);
          insertStatement(choices,afterstmt,location,true);
        }
        else{
          insertStatement(choices,afterstmt,location,true);
          insertStatement(choices,callStmt6,location, true);
        }
      }
    }
    popScopeStack();
  }
  return choices;
  
  printf("Variable Declarations complete.\n");
  //        popScopeStack();
  
}
string plus1(string a , string b){
  char* temp = new char[a.size()+1];
  char* temp2 = new char[b.size()+1];
  std::copy(a.begin(),a.end(),temp);
  std::copy(b.begin(),b.end(),temp2);
  //*temp[0]='\0';
  char* var = strcat(temp,temp2);
  std::string total(var);
  return total;
}
void buildMPIFunctions(SgBasicBlock* func_body, SgForStatement* loop)
{
  SgFunctionDeclaration* mainFunc = findMain(getProject());
  SgBasicBlock* body= mainFunc->get_definition()->get_body();
  pushScopeStack(body);
  if(body!=NULL)
  {
    SgExprListExp* args ;
    if(lookupVariableSymbolInParentScopes(SgName("argc"),body)!=NULL)
      args = buildExprListExp(buildAddressOfOp(buildVarRefExp(SgName("argc"),body)), buildAddressOfOp(buildVarRefExp(SgName("argv"), body)));
    //              SgExpression* nul = buildNullExpression();
    //              cout << isSgNode(nul)->unparseToString()<<endl;
    else args = buildExprListExp(buildOpaqueVarRefExp("NULL"),buildOpaqueVarRefExp("NULL"));
    if(body->get_statements().size() > 1)
    {
      SgExprStatement* callStmt1 = buildFunctionCallStmt(SgName("MPI_Init"),buildIntType(),args,body);
      SgExprStatement* callStmt_2 = buildFunctionCallStmt(SgName("MPI_Finalize"),buildIntType(), buildExprListExp(),body);
      SgStatement* lastDeclarationStatement = getFirstStatement(body);
      while(isSgVariableDeclaration(lastDeclarationStatement)!=NULL)
        lastDeclarationStatement = getNextStatement(lastDeclarationStatement);
      
      if (lastDeclarationStatement != NULL)
      {
        insertStatementAfter (lastDeclarationStatement, callStmt1);
      }
      SgStatement* last = getLastStatement(body);
      insertStatementBefore(last,callStmt_2);
    }
  }
  popScopeStack();
  printf("Function Declaration Complete.\n");
  
}
void upperAndLowerLimitValues_MPI(SgExpression* upperbound,SgExpression* lowerbound,SgForStatement* last,int count){
  pushScopeStack(last->get_parent());
  char* upperLim = (char*)malloc(50);
  sprintf(upperLim,"rose_upper_limit%d",count);
  char* lowerLim = (char*)malloc(50);
  sprintf(lowerLim,"rose_lower_limit%d",count);
  SgVariableDeclaration* variableDecl = buildVariableDeclaration(upperLim,buildIntType());
  prependStatement(variableDecl,last->get_scope());
  variableDecl = buildVariableDeclaration(lowerLim,buildIntType());
  prependStatement(variableDecl,last->get_scope());
  SgExpression* init_exp = buildAddOp(buildMultiplyOp(buildVarRefExp("rose_rank"),buildDivideOp(buildSubtractOp(upperbound,lowerbound),buildOpaqueVarRefExp("rose_size"))),lowerbound);
  SgExprStatement* dec = buildAssignStatement(buildVarRefExp(lowerLim),init_exp);
  SgExprStatement* conditional = buildExprStatement(buildEqualityOp(buildOpaqueVarRefExp("rose_rank"),buildSubtractOp(buildOpaqueVarRefExp("rose_size"),buildIntVal(1))));
  SgExprStatement* true_body = buildAssignStatement(buildVarRefExp(upperLim),buildAddOp(buildVarRefExp(lowerLim),buildAddOp(buildDivideOp(buildSubtractOp((upperbound),lowerbound),buildOpaqueVarRefExp("rose_size")),buildModOp((upperbound),buildOpaqueVarRefExp("rose_size")))));
  SgExprStatement* false_body = buildAssignStatement(buildVarRefExp(upperLim),buildAddOp(buildVarRefExp(lowerLim),buildDivideOp(buildSubtractOp((upperbound),lowerbound),buildOpaqueVarRefExp("rose_size"))));
  SgIfStmt *ifstmt = buildIfStmt (conditional, true_body, false_body);
  insertStatementBefore(last,dec);
  insertStatementBefore(last,ifstmt);
  popScopeStack();
}
